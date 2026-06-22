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
    const dotsWrap = document.getElementById("heroDots");
    let idx = 0, timer = null;

    // One clickable indicator dot per slide (kept in sync inside go()).
    const dots = slides.map((_, i) => {
      if (!dotsWrap) return null;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "hero__dot" + (i === 0 ? " is-active" : "");
      b.setAttribute("aria-label", "Foto " + (i + 1));
      b.addEventListener("click", () => { go(i); restart(); });
      dotsWrap.appendChild(b);
      return b;
    });

    function go(n) {
      slides[idx].classList.remove("is-active");
      dots[idx] && dots[idx].classList.remove("is-active");
      idx = (n + slides.length) % slides.length;
      slides[idx].classList.add("is-active");
      dots[idx] && dots[idx].classList.add("is-active");
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

  // ---- Motion & polish ----------------------------------------------------
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hasIO = "IntersectionObserver" in window;

  // Nav: solidify after scrolling past the top.
  const nav = document.getElementById("nav");
  if (nav) {
    const onScroll = () => nav.classList.toggle("is-scrolled", window.scrollY > 60);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // Scroll-reveal: fade/rise elements as they enter the viewport, staggered
  // within each grid/row. Final state matches the static layout exactly.
  const revealEls = document.querySelectorAll(
    ".feature, .room-card, .review, .split > div, " +
    "section > .container > .center, .gallery, .bookbar, .detail-grid > div");
  if (revealEls.length) {
    if (reduceMotion || !hasIO) {
      revealEls.forEach((el) => el.classList.add("reveal", "is-in"));
    } else {
      const seen = new Map();
      revealEls.forEach((el) => {
        el.classList.add("reveal");
        const n = seen.get(el.parentElement) || 0;
        el.style.setProperty("--d", (n % 6) * 70 + "ms");
        seen.set(el.parentElement, n + 1);
      });
      const io = new IntersectionObserver((entries, obs) => {
        entries.forEach((e) => {
          if (e.isIntersecting) { e.target.classList.add("is-in"); obs.unobserve(e.target); }
        });
      }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
      revealEls.forEach((el) => io.observe(el));
    }
  }

  // Count-up: animate a numeric element from 0 to its current value, once,
  // when it scrolls into view (e.g. the average rating).
  function countUp(el) {
    const raw = (el.textContent || "").trim();
    const m = raw.match(/([\d.,]+)/);
    if (!m) return;
    const numStr = m[1];
    const target = parseFloat(numStr.replace(",", "."));
    if (!isFinite(target)) return;
    const decimals = (numStr.split(/[.,]/)[1] || "").length;
    const prefix = raw.slice(0, m.index);
    const suffix = raw.slice(m.index + numStr.length);
    const t0 = performance.now(), dur = 1100;
    (function frame(t) {
      const p = Math.min(1, (t - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
      if (p < 1) requestAnimationFrame(frame); else el.textContent = raw;
    })(t0);
  }

  const nums = document.querySelectorAll(".rating-big .num");
  if (nums.length && hasIO && !reduceMotion) {
    const nio = new IntersectionObserver((entries, obs) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { countUp(e.target); obs.unobserve(e.target); }
      });
    }, { threshold: 0.6 });
    nums.forEach((el) => nio.observe(el));
  }
})();
