// Shared front-end behaviour: sane date minimums + mobile nav.
(function () {
  "use strict";
  const today = new Date().toISOString().slice(0, 10);

  // Every check-in defaults to today as minimum; check-out follows check-in.
  document.querySelectorAll('input[type="date"]').forEach((el) => {
    if (!el.min) el.min = today;
  });

  // Keep checkout strictly after checkin wherever both exist.
  function linkDates(inEl, outEl) {
    if (!inEl || !outEl) return;
    const sync = () => {
      if (!inEl.value) return;
      const next = new Date(inEl.value);
      next.setDate(next.getDate() + 1);
      const min = next.toISOString().slice(0, 10);
      outEl.min = min;
      if (outEl.value && outEl.value <= inEl.value) outEl.value = min;
    };
    inEl.addEventListener("change", sync);
  }
  linkDates(document.getElementById("ci"), document.getElementById("co"));
  linkDates(document.getElementById("checkin"), document.getElementById("checkout"));
  linkDates(document.getElementById("hb-in"), document.getElementById("hb-out"));

  // Close mobile menu after tapping a link.
  document.querySelectorAll(".nav__links a").forEach((a) =>
    a.addEventListener("click", () =>
      document.getElementById("nav").classList.remove("is-open")));

  // Hero carousel: crossfade with side arrows + autoplay.
  const car = document.getElementById("heroCarousel");
  if (car) {
    const slides = [...car.querySelectorAll(".hero__slide")];
    let idx = 0, timer = null;
    function go(n) {
      slides[idx].classList.remove("is-active");
      idx = (n + slides.length) % slides.length;
      slides[idx].classList.add("is-active");
    }
    function restart() {
      clearInterval(timer);
      timer = setInterval(() => go(idx + 1), 5500);
    }
    const prev = document.getElementById("heroPrev");
    const next = document.getElementById("heroNext");
    prev && prev.addEventListener("click", () => { go(idx - 1); restart(); });
    next && next.addEventListener("click", () => { go(idx + 1); restart(); });
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (slides.length > 1 && !reduce) restart();
    // Pause autoplay while the cursor is over the hero, resume when it leaves.
    const hero = car.closest(".hero");
    hero && hero.addEventListener("mouseenter", () => clearInterval(timer));
    hero && hero.addEventListener("mouseleave", restart);
  }
})();
