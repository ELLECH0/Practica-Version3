import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
from jinja2 import pass_context
from urllib.parse import urlencode
import hashlib
import hmac
import secrets


def generate_password_hash(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000).hex()
    return f'pbkdf2:sha256:310000${salt}${digest}'

def check_password_hash(encoded, password):
    try:
        method, rest = encoded.split('$', 1)
        salt, digest = rest.split('$', 1)
        if method.startswith('scrypt:'):
            _, n, r, p = method.split(':')
            calculated = hashlib.scrypt(password.encode(), salt=salt.encode(), n=int(n), r=int(r), p=int(p), maxmem=128 * 1024 * 1024).hex()
        elif method.startswith('pbkdf2:'):
            _, algo, iterations = method.split(':')
            calculated = hashlib.pbkdf2_hmac(algo, password.encode(), salt.encode(), int(iterations)).hex()
        else:
            return False
        return hmac.compare_digest(calculated, digest)
    except (ValueError, TypeError):
        return False
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'sportrent.db'
ROLES = {'client': 'Клиент', 'manager': 'Менеджер', 'admin': 'Администратор'}
STATUSES = {'pending': 'Ожидает подтверждения',
 'confirmed': 'Подтверждено',
 'issued': 'Выдано',
 'returned': 'Возвращено',
 'cancelled': 'Отменено',
 'overdue': 'Просрочено'}
ACTIVE_STATUSES = ('pending', 'confirmed', 'issued', 'overdue')
CONDITIONS = {'new': 'Новое', 'good': 'Хорошее', 'worn': 'С износом', 'broken': 'Требует ремонта'}
UNIT_STATUSES = {'available': 'На складе', 'rented': 'В аренде', 'repair': 'В ремонте', 'written_off': 'Списано'}
MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'client',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    icon TEXT NOT NULL DEFAULT 'box'
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price_per_day INTEGER NOT NULL,
    deposit INTEGER NOT NULL DEFAULT 0,
    qty_total INTEGER NOT NULL DEFAULT 1,
    image TEXT NOT NULL DEFAULT 'box.svg',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    inventory_no TEXT NOT NULL UNIQUE,
    condition TEXT NOT NULL DEFAULT 'good',
    status TEXT NOT NULL DEFAULT 'available',
    note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    equipment_id INTEGER NOT NULL REFERENCES equipment(id),
    unit_id INTEGER REFERENCES units(id),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    days INTEGER NOT NULL,
    qty INTEGER NOT NULL DEFAULT 1,
    total_price INTEGER NOT NULL,
    deposit INTEGER NOT NULL DEFAULT 0,
    penalty INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    condition_out TEXT,
    condition_in TEXT,
    comment TEXT NOT NULL DEFAULT '',
    manager_id INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    equipment_id INTEGER NOT NULL REFERENCES equipment(id),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    qty INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id, equipment_id, start_date, end_date)
);

CREATE INDEX IF NOT EXISTS idx_bookings_equipment ON bookings(equipment_id, status, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id, status);
"""
app = FastAPI(title='СпортПрокат API', version='2.0.0', description='Система аренды спортивного, туристического и строительного оборудования')
app.add_middleware(SessionMiddleware, secret_key=os.getenv('SECRET_KEY', 'change-this-secret-in-production'), max_age=60 * 60 * 24 * 7)
app.mount('/static', StaticFiles(directory=BASE_DIR / 'static'), name='static')
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))

def money(v):
    return f'{int(v or 0):,}'.replace(',', ' ') + ' ₽'

def rdate(v):
    if not v:
        return '—'
    try:
        return date.fromisoformat(str(v)[:10]).strftime('%d.%m.%Y')
    except ValueError:
        return str(v)

def rdatetime(v):
    if not v:
        return '—'
    try:
        return datetime.fromisoformat(str(v)).strftime('%d.%m.%Y %H:%M')
    except ValueError:
        return str(v)

@pass_context
def flask_url_for(ctx, name, **params):
    route = next((r for r in app.routes if getattr(r, 'name', None) == name), None)
    if route is None:
        raise RuntimeError(f'Unknown route: {name}')
    path_keys = set(getattr(route, 'param_convertors', {}).keys())
    path_params = {k: v for k, v in params.items() if k in path_keys}
    query = {k: v for k, v in params.items() if k not in path_keys and v is not None}
    url = str(ctx['request'].url_for(name, **path_params))
    return url + ('?' + urlencode(query) if query else '')
templates.env.globals['url_for'] = flask_url_for
templates.env.filters['money'] = money
templates.env.filters['rdate'] = rdate
templates.env.filters['datetime'] = rdatetime

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def get_db():
    db = connect()
    try:
        yield db
    finally:
        db.close()

def init_db():
    fresh = not DB_PATH.exists()
    db = connect()
    db.executescript(SCHEMA)
    if fresh or db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        seed(db)
    db.commit()
    db.close()

def seed(db):
    users = [('Администратор', 'admin@rent.ru', '+7 900 000-00-01', 'admin123', 'admin'),
 ('Менеджер Ольга', 'manager@rent.ru', '+7 900 000-00-02', 'manager123', 'manager'),
 ('Иван Петров', 'client@rent.ru', '+7 900 000-00-03', 'client123', 'client'),
 ('Мария Соколова', 'maria@mail.ru', '+7 900 111-22-33', 'client123', 'client')]
    for name, email, phone, pwd, role in users:
        db.execute('INSERT INTO users (name, email, phone, password_hash, role) VALUES (?,?,?,?,?)', (name, email, phone, generate_password_hash(pwd), role))
    categories = [('Спорт', 'sport', 'bike'), ('Туризм', 'tourism', 'tent'), ('Строительство', 'build', 'drill')]
    for name, slug, icon in categories:
        db.execute('INSERT INTO categories (name, slug, icon) VALUES (?,?,?)', (name, slug, icon))
    cat = {r['slug']: r['id'] for r in db.execute('SELECT id, slug FROM categories')}
    equipment = [('Горный велосипед Trek Marlin',
  'sport',
  'Горный велосипед с алюминиевой рамой, 21 скорость, дисковые тормоза. Подходит для '
  'города и лёгкого бездорожья.',
  1900,
  10000,
  3,
  'bike.svg'),
 ('Электросамокат Kugoo M4',
  'sport',
  'Мощный электросамокат с запасом хода 45 км. Шлем и защита входят в комплект.',
  1200,
  8000,
  4,
  'scooter.svg'),
 ('Сноуборд Burton Custom',
  'sport',
  'Универсальный сноуборд 158 см с креплениями. Ботинки подбираются по размеру.',
  1500,
  12000,
  2,
  'snowboard.svg'),
 ('Палатка 4-местная',
  'tourism',
  'Двухслойная палатка с тамбуром, ветрозащита и москитные сетки. Вес 4,2 кг.',
  800,
  5000,
  5,
  'tent.svg'),
 ('Спальный мешок-кокон',
  'tourism',
  'Комфортная температура до −5 °C, утеплитель синтепух, компрессионный чехол.',
  300,
  2000,
  8,
  'sleeping.svg'),
 ('Туристический рюкзак 70 л',
  'tourism',
  'Анатомическая спинка, дождевик в комплекте, регулировка по росту.',
  350,
  3000,
  6,
  'backpack.svg'),
 ('SUP-борд с веслом',
  'tourism',
  'Надувной SUP 320 см, насос и гермомешок в комплекте. Максимальная нагрузка 130 кг.',
  1600,
  9000,
  3,
  'sup.svg'),
 ('Байдарка двухместная',
  'tourism',
  'Каркасно-надувная байдарка с юбками и вёслами. Сборка за 15 минут.',
  2200,
  15000,
  2,
  'kayak.svg'),
 ('Перфоратор Bosch GBH 2-26',
  'build',
  'Ударная мощность 2,7 Дж, набор буров и зубил, кейс. Работает от сети 220 В.',
  900,
  6000,
  4,
  'drill.svg'),
 ('Бетономешалка 160 л',
  'build',
  'Гравитационная бетономешалка, венец из чугуна, двигатель 650 Вт.',
  1800,
  7000,
  3,
  'mixer.svg'),
 ('Строительные леса, секция',
  'build',
  'Рама 2×1 м с настилом и диагоналями. Сборка сертифицирована для высотных работ.',
  450,
  4000,
  10,
  'scaffold.svg'),
 ('Бензогенератор 3 кВт',
  'build',
  'Генератор с ручным запуском, бак 15 л, защита от перегрузки. Выдаётся с канистрой.',
  2200,
  15000,
  2,
  'generator.svg')]
    for name, slug, desc, price, deposit, qty, image in equipment:
        cur = db.execute('INSERT INTO equipment (category_id, name, description, price_per_day,\n               deposit, qty_total, image) VALUES (?,?,?,?,?,?,?)', (cat[slug], name, desc, price, deposit, qty, image))
        eq_id = cur.lastrowid
        for i in range(1, qty + 1):
            db.execute('INSERT INTO units (equipment_id, inventory_no, condition, status) VALUES (?,?,?,?)', (eq_id, f'SP-{eq_id:03d}-{i:02d}', 'new' if i == 1 else 'good', 'available'))
    client = db.execute("SELECT id FROM users WHERE email='client@rent.ru'").fetchone()['id']
    maria = db.execute("SELECT id FROM users WHERE email='maria@mail.ru'").fetchone()['id']
    manager = db.execute("SELECT id FROM users WHERE email='manager@rent.ru'").fetchone()['id']
    eq = {r['name']: (r['id'], r['price_per_day'], r['deposit']) for r in db.execute('SELECT * FROM equipment')}
    today = date.today()
    # Прошлые возвращённые аренды — данные для графиков.
    history = [('Горный велосипед Trek Marlin', 150, 152, 'returned', client, 2), ('Палатка 4-местная', 120, 123, 'returned', maria, 1), ('Перфоратор Bosch GBH 2-26', 95, 97, 'returned', client, 3), ('Спальный мешок-кокон', 80, 82, 'returned', maria, 2), ('Бетономешалка 160 л', 60, 63, 'returned', client, 4), ('SUP-борд с веслом', 45, 46, 'returned', maria, 1), ('Электросамокат Kugoo M4', 30, 32, 'returned', client, 5), ('Строительные леса, секция', 12, 20, 'returned', maria, 3), ('Туристический рюкзак 70 л', 5, 8, 'returned', client, 1)]
    for name, start_ago, end_ago, status, user_id, qty in history:
        eq_id, price, deposit = eq[name]
        start = today - timedelta(days=max(start_ago, end_ago))
        end = today - timedelta(days=min(start_ago, end_ago))
        days = (end - start).days + 1
        total = price * days * qty
        created = datetime.combine(start, datetime.min.time()) - timedelta(days=2)
        db.execute('INSERT INTO bookings (user_id, equipment_id, start_date, end_date, days, qty,\n               total_price, deposit, status, condition_out, condition_in, manager_id, created_at)\n               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', (user_id, eq_id, start.isoformat(), end.isoformat(), days, qty, total, deposit, status, 'good', 'good', manager, created.isoformat(sep=' ')))
    # Текущие брони: одна подтверждена, одна ожидает.
    plan = [('Палатка 4-местная', 2, 4, 'confirmed', client), ('Бензогенератор 3 кВт', 3, 6, 'pending', maria)]
    for name, start_in, end_in, status, user_id in plan:
        eq_id, price, deposit = eq[name]
        start = today + timedelta(days=start_in)
        end = today + timedelta(days=end_in)
        days = (end - start).days + 1
        db.execute('INSERT INTO bookings (user_id, equipment_id, start_date, end_date, days, qty,\n               total_price, deposit, status) VALUES (?,?,?,?,?,?,?,?,?)', (user_id, eq_id, start.isoformat(), end.isoformat(), days, 1, price * days, deposit, status))
    db.commit()

def parse_date(v):
    try:
        return date.fromisoformat((v or '').strip())
    except (ValueError, TypeError):
        return None

def calc_days(a, b):
    return (b - a).days + 1

def booked_qty(db, eid, start, end, exclude_id=None):
    marks = ','.join(('?' for _ in ACTIVE_STATUSES))
    sql = f'SELECT COALESCE(SUM(qty),0) FROM bookings WHERE equipment_id=? AND status IN ({marks}) AND start_date<=? AND end_date>=?'
    args = [eid, *ACTIVE_STATUSES, end.isoformat(), start.isoformat()]
    if exclude_id:
        sql += ' AND id<>?'
        args.append(exclude_id)
    return db.execute(sql, args).fetchone()[0]

def usable_qty(db, eid):
    total = db.execute('SELECT qty_total FROM equipment WHERE id=?', (eid,)).fetchone()
    if not total:
        return 0
    broken = db.execute("SELECT COUNT(*) FROM units WHERE equipment_id=? AND status IN ('repair','written_off')", (eid,)).fetchone()[0]
    return max(0, total['qty_total'] - broken)

def available_qty(db, eid, start, end, exclude_id=None):
    return max(0, usable_qty(db, eid) - booked_qty(db, eid, start, end, exclude_id))

def mark_overdue(db):
    db.execute("UPDATE bookings SET status='overdue' WHERE status='issued' AND end_date<?", (date.today().isoformat(),))
    db.commit()

def current_user(request, db):
    uid = request.session.get('user_id')
    return db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone() if uid else None

def flash(request, msg, category='info'):
    messages = request.session.get('_flashes', [])
    messages.append((category, msg))
    request.session['_flashes'] = messages

def context(request, db, **kwargs):
    user = current_user(request, db)
    return {'request': request, 'user': user, 'g': type('G', (), {'user': user})(), 'flashes': request.session.pop('_flashes', []), 'roles': ROLES, 'statuses': STATUSES, 'conditions': CONDITIONS, 'unit_statuses': UNIT_STATUSES, **kwargs}

def page(request, db, template_name, **kwargs):
    return templates.TemplateResponse(request=request, name=template_name, context=context(request, db, **kwargs))

def go(url):
    return RedirectResponse(url, status_code=303)

def require_user(request, db, roles=None):
    user = current_user(request, db)
    if not user:
        raise HTTPException(303, headers={'Location': '/login'})
    if roles and user['role'] not in roles:
        raise HTTPException(403, 'Недостаточно прав')
    return user

@app.get('/', response_class=HTMLResponse, name='index')
def index(request: Request):
    db = connect()
    popular = db.execute('SELECT e.*,c.name category_name FROM equipment e JOIN categories c ON c.id=e.category_id WHERE e.active=1 ORDER BY e.price_per_day DESC LIMIT 6').fetchall()
    categories = db.execute('SELECT * FROM categories ORDER BY id').fetchall()
    stats = {'items': db.execute('SELECT COUNT(*) FROM equipment WHERE active=1').fetchone()[0], 'units': db.execute("SELECT COUNT(*) FROM units WHERE status<>'written_off'").fetchone()[0], 'bookings': db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]}
    return page(request, db, 'index.html', popular=popular, categories=categories, stats=stats)

@app.get('/catalog', response_class=HTMLResponse, name='catalog')
def catalog(request: Request, category: str='', q: str='', price_min: str='', price_max: str='', sort: str='popular', date_from: str='', date_to: str=''):
    db = connect()
    sql = 'SELECT e.*,c.name category_name,c.slug category_slug FROM equipment e JOIN categories c ON c.id=e.category_id WHERE e.active=1'
    args = []
    if category:
        sql += ' AND c.slug=?'
        args.append(category)
    if q:
        sql += ' AND (e.name LIKE ? OR e.description LIKE ?)'
        args += [f'%{q}%', f'%{q}%']
    if price_min.isdigit():
        sql += ' AND e.price_per_day>=?'
        args.append(int(price_min))
    if price_max.isdigit():
        sql += ' AND e.price_per_day<=?'
        args.append(int(price_max))
    sql += ' ORDER BY ' + {'price_asc': 'e.price_per_day ASC', 'price_desc': 'e.price_per_day DESC', 'name': 'e.name ASC', 'popular': 'e.qty_total DESC,e.id ASC'}.get(sort, 'e.id ASC')
    rows = db.execute(sql, args).fetchall()
    start, end = (parse_date(date_from), parse_date(date_to))
    err = None
    if date_from or date_to:
        if not start or not end:
            err = 'Введите обе даты, чтобы проверить доступность.'
        elif end < start:
            err = 'Дата окончания раньше даты начала.'
        elif start < date.today():
            err = 'Дата начала уже прошла.'
    items = []
    for row in rows:
        d = dict(row)
        d['free'] = available_qty(db, row['id'], start, end) if start and end and (not err) else None
        items.append(d)
    cats = db.execute('SELECT * FROM categories ORDER BY id').fetchall()
    return page(request, db, 'catalog.html', items=items, categories=cats, category=category, q=q, price_min=price_min, price_max=price_max, sort=sort, date_from=date_from, date_to=date_to, date_error=err)

@app.get('/product/{equipment_id}', response_class=HTMLResponse, name='product')
def product(request: Request, equipment_id: int, date_from: str='', date_to: str=''):
    db = connect()
    item = db.execute('SELECT e.*,c.name category_name,c.slug category_slug FROM equipment e JOIN categories c ON c.id=e.category_id WHERE e.id=? AND e.active=1', (equipment_id,)).fetchone()
    if not item:
        raise HTTPException(404)
    a, b = (parse_date(date_from), parse_date(date_to))
    free = days = total = None
    err = None
    if date_from or date_to:
        if not a or not b:
            err = 'Укажите обе даты.'
        elif b < a:
            err = 'Дата возврата раньше даты получения.'
        elif a < date.today():
            err = 'Дата начала уже прошла.'
        else:
            days = calc_days(a, b)
            total = days * item['price_per_day']
            free = available_qty(db, equipment_id, a, b)
    similar = db.execute('SELECT id,name,price_per_day,image FROM equipment WHERE category_id=? AND id<>? AND active=1 LIMIT 3', (item['category_id'], equipment_id)).fetchall()
    return page(request, db, 'product.html', item=item, similar=similar, free=free, date_from=date_from, date_to=date_to, days=days, total=total, date_error=err)

@app.get('/register', response_class=HTMLResponse, name='register')
def register_get(request: Request):
    db = connect()
    if current_user(request, db):
        return go('/')
    return page(request, db, 'register.html', name='', email='', phone='')

@app.post('/register', name='register_post')
async def register_post(request: Request):
    form = await request.form()
    name = str(form.get('name', '')).strip()
    email = str(form.get('email', '')).strip().lower()
    phone = str(form.get('phone', '')).strip()
    password = str(form.get('password', ''))
    password2 = str(form.get('password2', ''))
    errors = []
    if len(name) < 2:
        errors.append('Укажите имя (минимум 2 символа).')
    if '@' not in email or '.' not in email.split('@')[-1]:
        errors.append('Введите корректный e-mail.')
    if len(phone) < 10:
        errors.append('Введите телефон для связи.')
    if len(password) < 6:
        errors.append('Пароль должен содержать минимум 6 символов.')
    if password != password2:
        errors.append('Пароли не совпадают.')
    db = connect()
    if not errors and db.execute('SELECT 1 FROM users WHERE email=?', (email,)).fetchone():
        errors.append('Пользователь с таким e-mail уже зарегистрирован.')
    if errors:
        for e in errors:
            flash(request, e, 'error')
        return page(request, db, 'register.html', name=name, email=email, phone=phone)
    cur = db.execute("INSERT INTO users(name,email,phone,password_hash,role) VALUES(?,?,?,?,'client')", (name, email, phone, generate_password_hash(password)))
    db.commit()
    request.session.clear()
    request.session['user_id'] = cur.lastrowid
    flash(request, 'Регистрация прошла успешно. Добро пожаловать!', 'success')
    return go('/account')

@app.get('/login', response_class=HTMLResponse, name='login')
def login_get(request: Request):
    db = connect()
    if current_user(request, db):
        return go('/')
    return page(request, db, 'login.html', email='')

@app.post('/login', name='login_post')
async def login_post(request: Request):
    form = await request.form()
    email = str(form.get('email', '')).strip().lower()
    password = str(form.get('password', ''))
    db = connect()
    user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    if not user or not check_password_hash(user['password_hash'], password):
        flash(request, 'Неверный e-mail или пароль.', 'error')
        return page(request, db, 'login.html', email=email)
    request.session.clear()
    request.session['user_id'] = user['id']
    flash(request, f"Здравствуйте, {user['name']}!", 'success')
    nxt = request.query_params.get('next', '')
    return go(nxt if nxt.startswith('/') else '/')

@app.get('/logout', name='logout')
def logout(request: Request):
    request.session.clear()
    flash(request, 'Вы вышли из аккаунта.', 'info')
    return go('/')

@app.get('/cart', response_class=HTMLResponse, name='cart')
def cart(request: Request):
    db = connect()
    user = require_user(request, db)
    rows = db.execute('SELECT ci.*,e.name,e.image,e.price_per_day,e.deposit FROM cart_items ci JOIN equipment e ON e.id=ci.equipment_id WHERE ci.user_id=? ORDER BY ci.id', (user['id'],)).fetchall()
    items = []
    total = 0
    problems = []
    for r in rows:
        a, b = (parse_date(r['start_date']), parse_date(r['end_date']))
        days = calc_days(a, b)
        price = days * r['price_per_day'] * r['qty']
        free = available_qty(db, r['equipment_id'], a, b)
        total += price
        if free < r['qty']:
            problems.append(f"«{r['name']}» недоступен на выбранные даты.")
        items.append({**dict(r), 'days': days, 'sum': price, 'free': free})
    return page(request, db, 'cart.html', items=items, total=total, problems=problems)

@app.post('/cart/add', name='cart_add')
async def cart_add(request: Request):
    db = connect()
    user = require_user(request, db)
    f = await request.form()
    if user['role'] != 'client':
        flash(request, 'Бронировать может только клиент.', 'warning')
        return go('/')
    eid = int(f.get('equipment_id', 0) or 0)
    a = parse_date(f.get('date_from'))
    b = parse_date(f.get('date_to'))
    if not eid or not a or (not b) or (b < a) or (a < date.today()) or (available_qty(db, eid, a, b) < 1):
        flash(request, 'Проверьте оборудование, даты и доступность.', 'error')
        return go(request.headers.get('referer', '/catalog'))
    db.execute('INSERT INTO cart_items(user_id,equipment_id,start_date,end_date,qty) VALUES(?,?,?,?,1) ON CONFLICT(user_id,equipment_id,start_date,end_date) DO NOTHING', (user['id'], eid, a.isoformat(), b.isoformat()))
    db.commit()
    flash(request, 'Добавлено в корзину.', 'success')
    return go('/cart')

@app.post('/cart/{item_id}/delete', name='cart_delete')
def cart_delete(request: Request, item_id: int):
    db = connect()
    user = require_user(request, db)
    db.execute('DELETE FROM cart_items WHERE id=? AND user_id=?', (item_id, user['id']))
    db.commit()
    return go('/cart')

@app.post('/checkout', name='checkout')
def checkout(request: Request):
    db = connect()
    user = require_user(request, db)
    rows = db.execute('SELECT ci.*,e.name,e.price_per_day,e.deposit FROM cart_items ci JOIN equipment e ON e.id=ci.equipment_id WHERE ci.user_id=?', (user['id'],)).fetchall()
    made = 0
    for r in rows:
        a, b = (parse_date(r['start_date']), parse_date(r['end_date']))
        if a and b and (b >= a) and (a >= date.today()) and (available_qty(db, r['equipment_id'], a, b) >= r['qty']):
            days = calc_days(a, b)
            db.execute("INSERT INTO bookings(user_id,equipment_id,start_date,end_date,days,qty,total_price,deposit,status) VALUES(?,?,?,?,?,?,?,?,'pending')", (user['id'], r['equipment_id'], a.isoformat(), b.isoformat(), days, r['qty'], days * r['price_per_day'] * r['qty'], r['deposit']))
            made += 1
    db.execute('DELETE FROM cart_items WHERE user_id=?', (user['id'],))
    db.commit()
    flash(request, f'Создано заявок: {made}.', 'success' if made else 'warning')
    return go('/account')

@app.post('/booking/{booking_id}/cancel', name='booking_cancel')
def booking_cancel(request: Request, booking_id: int):
    db = connect()
    user = require_user(request, db)
    row = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    if row['user_id'] != user['id'] and user['role'] not in ('manager', 'admin'):
        raise HTTPException(403)
    if row['status'] not in ('pending', 'confirmed'):
        flash(request, 'Эту бронь уже нельзя отменить.', 'warning')
    else:
        db.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
        db.commit()
        flash(request, 'Бронирование отменено.', 'success')
    return go(request.headers.get('referer', '/account'))

@app.get('/account', response_class=HTMLResponse, name='account')
def account(request: Request):
    db = connect()
    user = require_user(request, db)
    bookings = db.execute('SELECT b.*,e.name,e.image,e.price_per_day FROM bookings b JOIN equipment e ON e.id=b.equipment_id WHERE b.user_id=? ORDER BY b.created_at DESC', (user['id'],)).fetchall()
    active = [b for b in bookings if b['status'] in ('pending', 'confirmed', 'issued', 'overdue')]
    history = [b for b in bookings if b['status'] in ('returned', 'cancelled')]
    spent = sum((b['total_price'] + b['penalty'] for b in bookings if b['status'] == 'returned'))
    return page(request, db, 'account.html', bookings=bookings, active=active, history=history, spent=spent)

@app.get('/manager', response_class=HTMLResponse, name='manager')
def manager(request: Request, status: str='active'):
    db = connect()
    require_user(request, db, ('manager', 'admin'))
    mark_overdue(db)
    where = ''
    args = []
    if status == 'active':
        where = "WHERE b.status IN ('pending','confirmed','issued','overdue')"
    elif status in STATUSES:
        where = 'WHERE b.status=?'
        args = [status]
    bookings = db.execute(f'SELECT b.*,e.name,e.image,u.name client_name,u.phone client_phone FROM bookings b JOIN equipment e ON e.id=b.equipment_id JOIN users u ON u.id=b.user_id {where} ORDER BY b.created_at DESC', args).fetchall()
    counts = {r['status']: r['c'] for r in db.execute('SELECT status,COUNT(*) c FROM bookings GROUP BY status')}
    return page(request, db, 'manager.html', bookings=bookings, counts=counts, status=status)

@app.post('/manager/{booking_id}/confirm', name='manager_confirm')
def manager_confirm(request: Request, booking_id: int):
    db = connect()
    user = require_user(request, db, ('manager', 'admin'))
    row = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    if row['status'] == 'pending' and available_qty(db, row['equipment_id'], date.fromisoformat(row['start_date']), date.fromisoformat(row['end_date']), booking_id) >= 1:
        db.execute("UPDATE bookings SET status='confirmed',manager_id=? WHERE id=?", (user['id'], booking_id))
        db.commit()
        flash(request, 'Бронирование подтверждено.', 'success')
    else:
        flash(request, 'Нельзя подтвердить заявку: проверьте статус и наличие.', 'error')
    return go('/manager')

@app.post('/manager/{booking_id}/issue', name='manager_issue')
async def manager_issue(request: Request, booking_id: int):
    db = connect()
    user = require_user(request, db, ('manager', 'admin'))
    f = await request.form()
    row = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    unit = db.execute("SELECT * FROM units WHERE equipment_id=? AND status='available' ORDER BY id LIMIT 1", (row['equipment_id'],)).fetchone()
    cond = f.get('condition_out', 'good')
    if row['status'] == 'confirmed' and unit:
        db.execute("UPDATE bookings SET status='issued',unit_id=?,condition_out=?,manager_id=? WHERE id=?", (unit['id'], cond if cond in CONDITIONS else 'good', user['id'], booking_id))
        db.execute("UPDATE units SET status='rented' WHERE id=?", (unit['id'],))
        db.commit()
        flash(request, 'Оборудование выдано.', 'success')
    else:
        flash(request, 'Нельзя выдать оборудование.', 'error')
    return go('/manager')

@app.post('/manager/{booking_id}/return', name='manager_return')
async def manager_return(request: Request, booking_id: int):
    db = connect()
    user = require_user(request, db, ('manager', 'admin'))
    f = await request.form()
    row = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    cond = f.get('condition_in', 'good')
    penalty = max(0, int(f.get('penalty', 0) or 0))
    if row['status'] not in ('issued', 'overdue'):
        flash(request, 'Оборудование не числится выданным.', 'error')
        return go('/manager')
    end = date.fromisoformat(row['end_date'])
    if date.today() > end:
        penalty = max(penalty, (date.today() - end).days * max(100, row['total_price'] // max(row['days'], 1) // 2))
    if row['unit_id']:
        db.execute('UPDATE units SET status=?,condition=? WHERE id=?', ('repair' if cond == 'broken' else 'available', cond if cond in CONDITIONS else 'good', row['unit_id']))
    db.execute("UPDATE bookings SET status='returned',condition_in=?,penalty=?,manager_id=? WHERE id=?", (cond, penalty, user['id'], booking_id))
    db.commit()
    flash(request, 'Возврат оформлен.', 'success')
    return go('/manager')

@app.get('/warehouse', response_class=HTMLResponse, name='warehouse')
def warehouse(request: Request, category: str=''):
    db = connect()
    require_user(request, db, ('manager', 'admin'))
    sql = 'SELECT e.id,e.name,e.qty_total,e.image,c.name category_name,c.slug category_slug FROM equipment e JOIN categories c ON c.id=e.category_id'
    args = []
    if category:
        sql += ' WHERE c.slug=?'
        args = [category]
    equipment = db.execute(sql + ' ORDER BY c.id,e.name', args).fetchall()
    units = db.execute('SELECT u.*,e.name,e.id equipment_id FROM units u JOIN equipment e ON e.id=u.equipment_id ORDER BY e.name,u.inventory_no').fetchall()
    grouped = {}
    for u in units:
        grouped.setdefault(u['equipment_id'], []).append(u)
    cats = db.execute('SELECT * FROM categories ORDER BY id').fetchall()
    return page(request, db, 'warehouse.html', equipment=equipment, grouped=grouped, categories=cats, category=category)

@app.post('/warehouse/unit/add', name='unit_add')
async def unit_add(request: Request):
    db = connect()
    require_user(request, db, ('manager', 'admin'))
    f = await request.form()
    eid = int(f.get('equipment_id', 0))
    inv = str(f.get('inventory_no', '')).strip()
    cond = f.get('condition', 'good')
    try:
        db.execute('INSERT INTO units(equipment_id,inventory_no,condition) VALUES(?,?,?)', (eid, inv, cond))
        db.execute('UPDATE equipment SET qty_total=qty_total+1 WHERE id=?', (eid,))
        db.commit()
        flash(request, 'Единица добавлена.', 'success')
    except sqlite3.IntegrityError:
        flash(request, 'Проверьте оборудование и инвентарный номер.', 'error')
    return go('/warehouse')

@app.post('/warehouse/unit/{unit_id}/status', name='unit_status')
async def unit_status(request: Request, unit_id: int):
    db = connect()
    require_user(request, db, ('manager', 'admin'))
    f = await request.form()
    status = f.get('status', '')
    row = db.execute('SELECT * FROM units WHERE id=?', (unit_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    if row['status'] != 'rented' and status in UNIT_STATUSES:
        db.execute('UPDATE units SET status=? WHERE id=?', (status, unit_id))
        db.commit()
    return go('/warehouse')

@app.get('/admin', response_class=HTMLResponse, name='admin')
def admin(request: Request, tab: str='equipment'):
    db = connect()
    require_user(request, db, ('admin',))
    equipment = db.execute('SELECT e.*,c.name category_name FROM equipment e JOIN categories c ON c.id=e.category_id ORDER BY e.id').fetchall()
    categories = db.execute('SELECT c.*,COUNT(e.id) used FROM categories c LEFT JOIN equipment e ON e.category_id=c.id GROUP BY c.id ORDER BY c.id').fetchall()
    users = db.execute('SELECT * FROM users ORDER BY id').fetchall()
    return page(request, db, 'admin.html', tab=tab, equipment=equipment, categories=categories, users=users)

@app.post('/admin/equipment/save', name='admin_equipment_save')
async def admin_equipment_save(request: Request):
    db = connect()
    require_user(request, db, ('admin',))
    f = await request.form()
    eid = int(f.get('id', 0) or 0)
    name = str(f.get('name', '')).strip()
    cat = int(f.get('category_id', 0) or 0)
    desc = str(f.get('description', ''))
    price = int(f.get('price_per_day', 0) or 0)
    deposit = int(f.get('deposit', 0) or 0)
    qty = max(1, int(f.get('qty_total', 1) or 1))
    image = str(f.get('image', 'box.svg'))
    active = 1 if f.get('active') else 0
    if not name or not cat or price <= 0:
        flash(request, 'Заполните название, категорию и цену.', 'error')
        return go('/admin')
    if eid:
        old = db.execute('SELECT qty_total FROM equipment WHERE id=?', (eid,)).fetchone()
        if not old:
            raise HTTPException(404)
        db.execute('UPDATE equipment SET name=?,category_id=?,description=?,price_per_day=?,deposit=?,image=?,active=?,qty_total=? WHERE id=?', (name, cat, desc, price, deposit, image, active, qty, eid))
        diff = qty - old['qty_total']
        for i in range(max(0, diff)):
            db.execute('INSERT INTO units(equipment_id,inventory_no) VALUES(?,?)', (eid, f"SP-{eid:03d}-{old['qty_total'] + i + 1:02d}-n"))
    else:
        cur = db.execute('INSERT INTO equipment(category_id,name,description,price_per_day,deposit,qty_total,image,active) VALUES(?,?,?,?,?,?,?,?)', (cat, name, desc, price, deposit, qty, image, active))
        eid = cur.lastrowid
        for i in range(1, qty + 1):
            db.execute('INSERT INTO units(equipment_id,inventory_no) VALUES(?,?)', (eid, f'SP-{eid:03d}-{i:02d}-n'))
    db.commit()
    flash(request, 'Карточка сохранена.', 'success')
    return go('/admin')

@app.post('/admin/equipment/{eq_id}/delete', name='admin_equipment_delete')
def admin_equipment_delete(request: Request, eq_id: int):
    db = connect()
    require_user(request, db, ('admin',))
    active = db.execute("SELECT COUNT(*) FROM bookings WHERE equipment_id=? AND status IN ('pending','confirmed','issued','overdue')", (eq_id,)).fetchone()[0]
    if not active:
        db.execute('DELETE FROM equipment WHERE id=?', (eq_id,))
        db.commit()
    else:
        flash(request, 'Нельзя удалить оборудование с активными бронями.', 'error')
    return go('/admin')

@app.post('/admin/category/add', name='admin_category_add')
async def admin_category_add(request: Request):
    db = connect()
    require_user(request, db, ('admin',))
    f = await request.form()
    try:
        db.execute('INSERT INTO categories(name,slug) VALUES(?,?)', (str(f.get('name', '')).strip(), str(f.get('slug', '')).strip().lower()))
        db.commit()
    except sqlite3.IntegrityError:
        flash(request, 'Такая категория уже существует.', 'error')
    return go('/admin?tab=categories')

@app.post('/admin/category/{cat_id}/delete', name='admin_category_delete')
def admin_category_delete(request: Request, cat_id: int):
    db = connect()
    require_user(request, db, ('admin',))
    if db.execute('SELECT COUNT(*) FROM equipment WHERE category_id=?', (cat_id,)).fetchone()[0] == 0:
        db.execute('DELETE FROM categories WHERE id=?', (cat_id,))
        db.commit()
    return go('/admin?tab=categories')

@app.post('/admin/user/{user_id}/role', name='admin_user_role')
async def admin_user_role(request: Request, user_id: int):
    db = connect()
    me = require_user(request, db, ('admin',))
    f = await request.form()
    role = f.get('role', '')
    if user_id != me['id'] and role in ROLES:
        db.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))
        db.commit()
    return go('/admin?tab=users')

@app.post('/admin/user/{user_id}/delete', name='admin_user_delete')
def admin_user_delete(request: Request, user_id: int):
    db = connect()
    me = require_user(request, db, ('admin',))
    if user_id != me['id'] and db.execute("SELECT COUNT(*) FROM bookings WHERE user_id=? AND status IN ('pending','confirmed','issued','overdue')", (user_id,)).fetchone()[0] == 0:
        db.execute('DELETE FROM cart_items WHERE user_id=?', (user_id,))
        db.execute('DELETE FROM users WHERE id=?', (user_id,))
        db.commit()
    return go('/admin?tab=users')

@app.get('/stats', response_class=HTMLResponse, name='stats')
def stats(request: Request):
    db = connect()
    require_user(request, db, ('manager', 'admin'))
    monthly = db.execute("SELECT substr(created_at,1,7) month,SUM(total_price) total FROM bookings WHERE status='returned' GROUP BY month ORDER BY month DESC LIMIT 6").fetchall()
    kpi = {'revenue': sum((x['total'] or 0 for x in monthly)), 'bookings': db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0], 'active': db.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('pending','confirmed','issued','overdue')").fetchone()[0], 'clients': db.execute("SELECT COUNT(*) FROM users WHERE role='client'").fetchone()[0], 'avg_check': 0, 'broken': db.execute("SELECT COUNT(*) FROM units WHERE status IN ('repair','written_off')").fetchone()[0]}
    return page(request, db, 'stats.html', revenue_chart='', status_chart='', top_chart='', kpi=kpi)

@app.get('/api/equipment')
def api_equipment(category: Optional[str]=None, q: Optional[str]=None):
    db = connect()
    sql = 'SELECT e.id,e.name,e.description,e.price_per_day,e.deposit,e.qty_total,e.image,c.name category,c.slug category_slug FROM equipment e JOIN categories c ON c.id=e.category_id WHERE e.active=1'
    args = []
    if category:
        sql += ' AND c.slug=?'
        args.append(category)
    if q:
        sql += ' AND e.name LIKE ?'
        args.append(f'%{q}%')
    return [dict(x) for x in db.execute(sql + ' ORDER BY e.id', args).fetchall()]

@app.get('/api/equipment/{eid}')
def api_equipment_detail(eid: int):
    db = connect()
    x = db.execute('SELECT * FROM equipment WHERE id=? AND active=1', (eid,)).fetchone()
    if not x:
        raise HTTPException(404, 'Оборудование не найдено')
    return dict(x)

@app.get('/api/categories')
def api_categories():
    db = connect()
    return [dict(x) for x in db.execute('SELECT * FROM categories ORDER BY id').fetchall()]

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'sportrent-fastapi'}
init_db()
