/* Direction C — animations Phase 1
   Source : 00_brief/dc/ANIMATIONS.md
   - #1 (carte hover) et #3 (bouton hover/active) → pure CSS dans components.css.
   - #2 (entrée carte au scroll), #4 (pulse pastille), #5 (score-bar fill)
     sont armés ici via Intersection Observer.

   Respect de prefers-reduced-motion : si l'utilisateur a la préférence,
   on rend tout immédiatement sans transition (les CSS désactivent en
   plus les transitions, double garde). */

(function () {
  'use strict';

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const cards = document.querySelectorAll('.offer-card');
  const STAGGER_MS = 60;
  const STAGGER_MAX = 6;

  function reveal(card, index) {
    const delay = Math.min(index, STAGGER_MAX) * STAGGER_MS;
    setTimeout(() => {
      card.classList.add('is-visible');

      // #4 — pulse pastille (200ms après l'apparition)
      const pill = card.querySelector('.acid-pill');
      if (pill) {
        setTimeout(() => pill.classList.add('is-popped'), 200);
      }

      // #5 — score-bar fill (250ms après l'apparition)
      const fill = card.querySelector('.score-bar > .fill');
      if (fill) {
        const score = parseFloat(fill.getAttribute('data-score') || '0');
        if (score > 0) {
          setTimeout(() => {
            fill.classList.add('is-filled');
            fill.style.width = score + '%';
          }, 250);
        }
      }
    }, delay);
  }

  if (reduceMotion) {
    // Tout visible immédiatement, pas d'animations gracieuses.
    cards.forEach(card => {
      card.classList.add('is-visible');
      const fill = card.querySelector('.score-bar > .fill');
      if (fill) {
        const score = parseFloat(fill.getAttribute('data-score') || '0');
        if (score > 0) fill.style.width = score + '%';
      }
    });
    return;
  }

  if (!('IntersectionObserver' in window)) {
    // Fallback : on révèle tout immédiatement.
    Array.from(cards).forEach((card, i) => reveal(card, i));
    return;
  }

  let visibleCount = 0;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        reveal(entry.target, visibleCount++);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  cards.forEach(card => observer.observe(card));
})();
