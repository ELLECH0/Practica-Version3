(function () {
  "use strict";

  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("nav");

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      toggle.setAttribute("aria-label", open ? "Закрыть меню" : "Меню");
      toggle.textContent = open ? "Закрыть" : "Меню";
    });

    nav.addEventListener("click", function (event) {
      if (event.target.tagName === "A" && nav.classList.contains("is-open")) {
        nav.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Меню");
        toggle.textContent = "Меню";
      }
    });
  }

  var form = document.getElementById("register-form");
  if (form) {
    var pwd = document.getElementById("password");
    var pwd2 = document.getElementById("password2");
    var error = document.getElementById("password-error");

    function checkMatch() {
      if (!pwd || !pwd2) return true;
      var match = pwd.value === pwd2.value;
      if (error) error.hidden = match || !pwd2.value;
      if (match) {
        pwd2.setCustomValidity("");
      } else {
        pwd2.setCustomValidity("Пароли не совпадают.");
      }
      return match;
    }

    if (pwd && pwd2) {
      pwd.addEventListener("input", checkMatch);
      pwd2.addEventListener("input", checkMatch);
    }

    form.addEventListener("submit", function (event) {
      if (!checkMatch()) {
        event.preventDefault();
        if (pwd2) pwd2.focus();
      }
    });
  }

  var pairs = document.querySelectorAll(".booking-form .field-row, .filters__form .field-row");

  function isoToday() {
    var now = new Date();
    var offset = now.getTimezoneOffset();
    return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10);
  }

  pairs.forEach(function (row) {
    var from = row.querySelector('input[name="date_from"]');
    var to = row.querySelector('input[name="date_to"]');
    if (!from || !to) return;

    var today = isoToday();
    if (!from.min) from.min = today;
    if (!to.min) to.min = today;

    from.addEventListener("change", function () {
      if (from.value) {
        to.min = from.value;
        if (to.value && to.value < from.value) to.value = from.value;
      }
    });

    to.addEventListener("change", function () {
      if (from.value && to.value && to.value < from.value) {
        to.value = from.value;
      }
    });
  });

  var calc = document.querySelector(".booking-form");
  if (calc) {
    var priceNode = document.querySelector(".product__price .price");
    var from = calc.querySelector('input[name="date_from"]');
    var to = calc.querySelector('input[name="date_to"]');

    var price = 0;
    if (priceNode) {
      var digits = priceNode.textContent.replace(/[^\d]/g, "");
      price = parseInt(digits, 10) || 0;
    }

    var preview = document.createElement("p");
    preview.className = "hint js-price-preview";
    calc.appendChild(preview);

    function updatePreview() {
      if (!from.value || !to.value || to.value < from.value || price <= 0) {
        preview.textContent = "";
        return;
      }
      var a = new Date(from.value + "T00:00:00");
      var b = new Date(to.value + "T00:00:00");
      var days = Math.round((b - a) / 86400000) + 1;
      var total = days * price;
      preview.textContent =
        "Предварительно: " + days + " сут. × " + price.toLocaleString("ru-RU") +
        " ₽ = " + total.toLocaleString("ru-RU") + " ₽";
    }

    if (from && to) {
      from.addEventListener("change", updatePreview);
      to.addEventListener("change", updatePreview);
      updatePreview();
    }
  }
})();
