// Booking form: live price estimate + guest-cap enforcement.
(function () {
  "use strict";
  const room = document.getElementById("room_id");
  const ci = document.getElementById("checkin");
  const co = document.getElementById("checkout");
  const guests = document.getElementById("guests");
  const est = document.getElementById("estimate");
  const estLabel = document.getElementById("estLabel");
  const estTotal = document.getElementById("estTotal");
  if (!room) return;

  const T = (s) => (window.I18N && window.I18N[s]) || s;
  const M = window.MONEY || { currency: "COP", rate: 1 };
  const fmtCOP = (cop) => M.currency === "USD"
    ? "US$" + Math.round(cop / M.rate).toLocaleString("en-US")
    : "$" + cop.toLocaleString("es-CO");
  const nights = () => {
    if (!ci.value || !co.value) return 0;
    const d = (new Date(co.value) - new Date(ci.value)) / 86400000;
    return d > 0 ? Math.round(d) : 0;
  };

  function update() {
    const opt = room.options[room.selectedIndex];
    const price = opt ? parseInt(opt.dataset.price || "0", 10) : 0;
    const max = opt ? parseInt(opt.dataset.max || "10", 10) : 10;
    if (max) { guests.max = max; if (+guests.value > max) guests.value = max; }
    const n = nights();
    if (price && n) {
      estLabel.textContent = `${fmtCOP(price)} × ${n} ${T("noche(s)")}`;
      estTotal.textContent = fmtCOP(price * n);
      est.style.display = "flex";
    } else {
      est.style.display = "none";
    }
  }

  [room, ci, co, guests].forEach((el) => el && el.addEventListener("change", update));
  update();
})();
