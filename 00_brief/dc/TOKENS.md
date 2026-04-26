# Direction C — Tokens (CSS variables)

```css
:root {
  /* Surfaces */
  --bg:        #FAFAF9;
  --surface:   #FFFFFF;

  /* Ink */
  --ink:       #0A0A0A;
  --ink-2:     #404040;
  --ink-3:     #737373;
  --ink-4:     #A3A3A3;

  /* Lines */
  --border:    #E5E5E5;
  --border-h:  #D4D4D4;

  /* Accent — teal */
  --teal:      #0F766E;
  --teal-h:    #115E59;
  --teal-bg:   #F0FDFA;

  /* Highlight — acide (réservé : promo, KPI, badges à valoriser) */
  --acid:      #D4FF4D;
  --acid-ink:  #1A2E00;

  /* Sémantique */
  --ok:        #16A34A;
  --err:       #DC2626;

  /* Shadows */
  --s1: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04);
  --s2: 0 2px 6px rgba(0,0,0,0.05), 0 12px 32px rgba(0,0,0,0.08);
  --ring-focus: 0 0 0 3px rgba(15,118,110,0.20);

  /* Espacements (base 4px) */
  --sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px; --sp-4: 16px;
  --sp-6: 24px; --sp-8: 32px; --sp-12: 48px; --sp-16: 64px; --sp-24: 96px;

  /* Radius */
  --r-sm: 6px; --r-md: 8px; --r-lg: 10px; --r-xl: 12px; --r-pill: 999px;
}

/* Typography */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

body {
  font-family: Inter, 'Helvetica Neue', system-ui, sans-serif;
  font-feature-settings: 'cv11', 'tnum';
  background: var(--bg);
  color: var(--ink);
}

/* Hiérarchie typo */
.t-display { font-size: 3rem; font-weight: 700; letter-spacing: -0.02em; line-height: 0.95; }
.t-h1      { font-size: 1.5rem; font-weight: 600; letter-spacing: -0.5px; }
.t-h2      { font-size: 1.125rem; font-weight: 600; letter-spacing: -0.2px; }
.t-body    { font-size: 0.95rem; font-weight: 400; line-height: 1.5; }
.t-body-strong { font-size: 0.95rem; font-weight: 500; }
.t-caption { font-size: 0.75rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-3); }
```

## Composants

### Carte d'offre (écran 2)
```css
.offer-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);    /* 12px */
  padding: var(--sp-6);          /* 24px */
  box-shadow: var(--s1);
  transition: all 200ms cubic-bezier(0.16, 1, 0.3, 1);
}
.offer-card:hover {
  border-color: var(--border-h);
  box-shadow: var(--s2);
  transform: translateY(-2px);
}
.offer-card:focus-visible {
  outline: none;
  border-color: var(--teal);
  box-shadow: var(--ring-focus);
}
.offer-card:active {
  background: #F5F5F4;
  transform: translateY(1px);
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);
}

.acid-pill {
  background: var(--acid);
  color: var(--acid-ink);
  font-weight: 700;
  font-size: 0.6875rem;
  padding: 3px 9px;
  border-radius: var(--r-pill);
}

.score-bar {
  height: 6px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--r-pill);
  overflow: hidden;
}
.score-bar > .fill { background: var(--teal); height: 100%; }

.btn-primary {
  height: 44px;
  background: var(--teal);
  color: #fff;
  border: none;
  border-radius: var(--r-lg);
  font-weight: 600;
  transition: background 150ms ease-out;
}
.btn-primary:hover { background: var(--teal-h); }
.btn-primary:focus-visible { box-shadow: var(--ring-focus); outline: none; }
```
