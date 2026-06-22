// Room-detail availability widget: checks /api/availability and, when free,
// sends the guest to the booking form with dates pre-filled.
(function () {
  "use strict";
  const box = document.getElementById("box");
  if (!box) return;
  const T = (s) => (window.I18N && window.I18N[s]) || s;

  const roomId = box.dataset.roomId;
  const slug = box.dataset.slug;
  const price = parseInt(box.dataset.price, 10);
  const ci = document.getElementById("ci");
  const co = document.getElementById("co");
  const g = document.getElementById("g");
  const msg = document.getElementById("avail");
  const totals = document.getElementById("totals");
  const btn = document.getElementById("reserve");

  const M = window.MONEY || { currency: "COP", rate: 1 };
  const fmtCOP = (cop) => M.currency === "USD"
    ? "US$" + Math.round(cop / M.rate).toLocaleString("en-US")
    : "$" + cop.toLocaleString("es-CO");
  let available = false;

  function setMsg(text, kind) {
    msg.textContent = text;
    msg.className = "avail-msg " + kind;
    msg.style.display = "block";
  }

  async function check() {
    if (!ci.value || !co.value || co.value <= ci.value) {
      totals.style.display = "none";
      btn.disabled = true;
      btn.textContent = T("Selecciona tus fechas");
      return;
    }
    btn.disabled = true;
    btn.textContent = T("Comprobando…");
    try {
      const url = `/api/availability?room_id=${roomId}&checkin=${ci.value}&checkout=${co.value}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("bad");
      const data = await res.json();
      available = data.available;
      if (available) {
        setMsg(T("✓ ¡Disponible para tus fechas!"), "ok");
        document.getElementById("nlabel").textContent =
          `${fmtCOP(price)} × ${data.nights} ${T("noche(s)")}`;
        document.getElementById("ntotal").textContent = fmtCOP(data.total_cop);
        document.getElementById("grand").textContent = fmtCOP(data.total_cop);
        totals.style.display = "block";
        btn.disabled = false;
        btn.textContent = T("Reservar estas fechas");
      } else {
        setMsg(T("No disponible para esas fechas. Prueba otras."), "no");
        totals.style.display = "none";
        btn.disabled = true;
        btn.textContent = T("No disponible");
      }
    } catch (e) {
      setMsg(T("No pudimos comprobar ahora. Intenta de nuevo."), "no");
      btn.disabled = true;
      btn.textContent = T("Reintentar");
    }
  }

  btn.addEventListener("click", () => {
    if (!available) { check(); return; }
    const q = new URLSearchParams({
      room: slug, checkin: ci.value, checkout: co.value, guests: g.value,
    });
    window.location = "/reservar?" + q.toString();
  });

  ci.addEventListener("change", check);
  co.addEventListener("change", check);
  check();
})();
