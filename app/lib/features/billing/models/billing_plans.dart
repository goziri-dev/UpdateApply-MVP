/// Checkout plan codes accepted by `POST /api/v1/billing/checkout`.
enum CheckoutPlan {
  payg,
  lite,
  plus;

  String get apiValue => name;
}

/// Visual / copy mode for comparison cards.
enum PlanCardKind { free, payg, lite, plus }

/// Static catalog matching `prototypes/paywall/` (prices + UX copy).
class PlanCatalogEntry {
  const PlanCatalogEntry({
    required this.kind,
    required this.name,
    required this.benefit,
    required this.price,
    required this.meta,
    required this.features,
    required this.badge,
    required this.ctaLabel,
    this.checkoutPlan,
    this.recommended = false,
    this.limited = false,
  });

  final PlanCardKind kind;
  final String name;
  final String benefit;
  final String price;
  final String meta;
  final List<String> features;
  final String badge;
  final String ctaLabel;
  final CheckoutPlan? checkoutPlan;
  final bool recommended;
  final bool limited;
}

/// Hub comparison: Free · PAYG · Lite · Plus (Lite recommended).
const List<PlanCatalogEntry> kCreditsHubPlans = [
  PlanCatalogEntry(
    kind: PlanCardKind.free,
    name: 'Free',
    benefit:
        'Try UpdateApply with a small lifetime grant — enough to see the fit.',
    price: '€0',
    meta: '3 tailorings · lifetime',
    features: [
      '3 CV tailorings on your account',
      'Full tailor + applications flow',
      'No monthly commitment',
    ],
    badge: 'Limited',
    ctaLabel: 'Stay free',
    limited: true,
  ),
  PlanCatalogEntry(
    kind: PlanCardKind.payg,
    name: 'Pay as you go',
    benefit: 'One more tailored resume when you need it — no subscription.',
    price: '€2.99',
    meta: '1 CV tailoring',
    features: [
      '1 additional tailoring',
      'Credits never expire',
      'Buy again anytime',
    ],
    badge: 'One-time',
    ctaLabel: '1 for €2.99',
    checkoutPlan: CheckoutPlan.payg,
  ),
  PlanCatalogEntry(
    kind: PlanCardKind.lite,
    name: 'Lite',
    benefit:
        'Steady monthly tailorings for an active search without overbuying.',
    price: '€9.99',
    meta: '10 tailorings / month',
    features: [
      '10 CV tailorings every month',
      'Best per-tailoring value for most',
      'Manage or cancel in Stripe portal',
    ],
    badge: 'Recommended',
    ctaLabel: 'Lite · 10/mo · €9.99',
    checkoutPlan: CheckoutPlan.lite,
    recommended: true,
  ),
  PlanCatalogEntry(
    kind: PlanCardKind.plus,
    name: 'Plus',
    benefit: 'More room when you’re applying across many roles each week.',
    price: '€14.99',
    meta: '25 tailorings / month',
    features: [
      '25 CV tailorings every month',
      'Lowest cost per tailor',
      'Manage or cancel in Stripe portal',
    ],
    badge: 'High volume',
    ctaLabel: 'Plus · 25/mo · €14.99',
    checkoutPlan: CheckoutPlan.plus,
  ),
];

/// Hard paywall rail: PAYG · Lite · Plus · Free (Maybe later).
const List<PlanCatalogEntry> kPaywallPlans = [
  PlanCatalogEntry(
    kind: PlanCardKind.payg,
    name: 'Pay as you go',
    benefit: 'One more tailored resume when you need it — no subscription.',
    price: '€2.99',
    meta: '1 CV tailoring',
    features: ['1 additional tailoring', 'Credits never expire'],
    badge: 'One-time',
    ctaLabel: '1 for €2.99',
    checkoutPlan: CheckoutPlan.payg,
  ),
  PlanCatalogEntry(
    kind: PlanCardKind.lite,
    name: 'Lite',
    benefit: 'Steady monthly tailorings for an active search.',
    price: '€9.99',
    meta: '10 tailorings / month',
    features: [
      '10 CV tailorings every month',
      'Best value for most job seekers',
    ],
    badge: 'Recommended',
    ctaLabel: 'Lite · 10/mo · €9.99',
    checkoutPlan: CheckoutPlan.lite,
    recommended: true,
  ),
  PlanCatalogEntry(
    kind: PlanCardKind.plus,
    name: 'Plus',
    benefit: 'More room when you’re applying across many roles.',
    price: '€14.99',
    meta: '25 tailorings / month',
    features: ['25 CV tailorings every month', 'Lowest cost per tailor'],
    badge: 'High volume',
    ctaLabel: 'Plus · 25/mo · €14.99',
    checkoutPlan: CheckoutPlan.plus,
  ),
  PlanCatalogEntry(
    kind: PlanCardKind.free,
    name: 'Free',
    benefit: 'Your lifetime grant is used up — stay browsing, or top up to tailor again.',
    price: '€0',
    meta: '3 tailorings · lifetime (used)',
    features: [
      'Browse jobs & applications',
      'No new tailorings until you top up',
    ],
    badge: 'Limited',
    ctaLabel: 'Maybe later',
    limited: true,
  ),
];
