# Animations annotées — Direction C (5 max, à implémenter en Phase 1+)

> Référence de subtilité : Stripe. Toutes les valeurs sont à reprendre telles quelles dans Claude Code.

## 1. Élévation de la carte d'offre au hover
- **Élément** : `.offer-card`
- **Déclencheur** : `:hover` (pointer)
- **Propriétés** : `transform: translateY(-2px)` · `box-shadow` (s1 → s2) · `border-color` (`#E5E5E5` → `#D4D4D4`)
- **Durée + easing** : `200ms cubic-bezier(0.16, 1, 0.3, 1)` (ease-out doux, type Stripe)

## 2. Apparition des cartes au scroll (page load + on enter viewport)
- **Élément** : chaque `.offer-card` dans la liste
- **Déclencheur** : entrée dans le viewport (IntersectionObserver, threshold 0.15)
- **Propriétés** : `opacity: 0 → 1` · `transform: translateY(8px) → translateY(0)`
- **Durée + easing** : `400ms cubic-bezier(0.16, 1, 0.3, 1)` · délai par carte de `60ms × index` (effet stagger, max 6 cartes)

## 3. Bouton CTA — feedback hover/active
- **Élément** : `.btn-primary` ("Voir le détail")
- **Déclencheur** : `:hover` puis `:active`
- **Propriétés hover** : `background: #0F766E → #115E59`
- **Propriétés active** : `transform: scale(0.98)`
- **Durée + easing** : `150ms ease-out` (hover) · `80ms ease-in` (active press)

## 4. Pastille acide — pulse subtil au mount
- **Élément** : `.acid-pill` ("Économisez 10 €")
- **Déclencheur** : à l'apparition de la carte (uniquement la première fois, pas à chaque re-render)
- **Propriétés** : `transform: scale(0.85) → scale(1.04) → scale(1)` · `opacity: 0 → 1`
- **Durée + easing** : `380ms cubic-bezier(0.34, 1.56, 0.64, 1)` (léger overshoot, attire l'œil sans agressivité), délai `200ms` après l'apparition de la carte

## 5. Score bar — fill animé au mount
- **Élément** : `.score-bar > .fill`
- **Déclencheur** : entrée de la carte dans le viewport (même observer que #2)
- **Propriétés** : `width: 0% → 84%` (la valeur cible vient de `offers.score / 10 * 100`)
- **Durée + easing** : `700ms cubic-bezier(0.22, 1, 0.36, 1)` · délai `250ms` (joue après l'élévation de la carte)

---

**Principes** :
- Une seule animation à la fois sur un élément donné (pas de transform + box-shadow simultanés sur la même propriété).
- Toutes les durées ≤ 700ms — au-delà, l'utilisateur perçoit la latence.
- Respect de `prefers-reduced-motion` : désactiver #2, #4, #5 si l'utilisateur a la préférence active. #1 et #3 restent (feedback essentiel).
