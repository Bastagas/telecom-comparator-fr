/* Graph d'évolution du prix (offer.php).
   Données : window.__priceHistory injecté par PHP.
   Bibliothèque : Chart.js (CDN) chargé par offer.php uniquement. */

(function () {
  'use strict';

  const data = window.__priceHistory;
  if (!Array.isArray(data) || data.length < 2) return;

  const canvas = document.getElementById('price-chart');
  if (!canvas || typeof Chart === 'undefined') return;

  const labels = data.map(p => {
    const d = new Date(p.captured_at);
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
  });
  const prices = data.map(p => p.price);

  const styles = getComputedStyle(document.documentElement);
  const teal = styles.getPropertyValue('--teal').trim() || '#0F766E';
  const ink3 = styles.getPropertyValue('--ink-3').trim() || '#737373';
  const border = styles.getPropertyValue('--border').trim() || '#E5E5E5';

  // Hex → rgba sans alpha (utile pour le fill teal sur lui-même).
  function hexToRgba(hex, alpha) {
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!m) return 'rgba(15,118,110,' + alpha + ')';
    const r = parseInt(m[1], 16), g = parseInt(m[2], 16), b = parseInt(m[3], 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  new Chart(canvas, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Prix mensuel (€)',
        data: prices,
        borderColor: teal,
        backgroundColor: hexToRgba(teal, 0.08),
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointBackgroundColor: teal,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600, easing: 'easeOutQuart' },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0A0A0A',
          padding: 8,
          callbacks: {
            label: (ctx) => ctx.parsed.y.toFixed(2).replace('.', ',') + ' €/mois',
          }
        }
      },
      scales: {
        x: {
          ticks: {
            color: ink3,
            maxTicksLimit: 6,
            font: { size: 11 },
          },
          grid: { display: false },
        },
        y: {
          ticks: {
            color: ink3,
            font: { size: 11 },
            stepSize: 0.5,
            callback: v => v.toFixed(2).replace('.', ',') + ' €',
          },
          grid: { color: border },
        }
      }
    }
  });
})();
