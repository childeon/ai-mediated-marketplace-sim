"""
ranking.py — Platform-internal scoring and LLM scoring functions.
All weights come from config so experiments can override them.
"""

from __future__ import annotations
from typing import List, Dict, Optional
import numpy as np

import config
from entities import Offer, Consumer, Intent, Platform
from choice import intent_fulfilment


# ── Normalisation helper ───────────────────────────────────────────────────────

def _norm(arr: np.ndarray) -> np.ndarray:
    """Min-max normalise; return zeros if range is zero."""
    mn, mx = arr.min(), arr.max()
    if mx == mn:
        return np.zeros_like(arr, dtype=float)
    return (arr - mn) / (mx - mn)


# ── Platform-internal ranking ──────────────────────────────────────────────────

def platform_score(offer: Offer, weights: Optional[Dict] = None) -> float:
    """
    Score an offer from the platform's perspective.
    Higher is better for the platform (and thus more likely to appear to consumers).
    """
    w = weights or config.PLATFORM_SCORE_WEIGHTS
    score = (
        w["quality"]           * offer.quality / config.QUALITY_SCALE
        + w["commission_rev"]  * (
            offer.menu_price * config.PLATFORM_PARAMS[offer.platform_id]["commission"] / 12.0
        )
        - w["neg_total_price"] * offer.total_price / 40.0
        - w["neg_delivery_time"] * offer.delivery_time / 90.0
        + w["promo_boost"]     * (offer.promo_discount / 5.0)
        + w["sponsored_boost"] * offer.sponsored_boost
    )
    return float(score)


def rank_offers_by_platform(offers: List[Offer],
                             platform_id: int,
                             top_n: int = 20,
                             cuisine_filter: Optional[str] = None) -> List[Offer]:
    """Return top_n offers for a given platform, sorted by platform score.
    If cuisine_filter is set, only offers matching that cuisine are returned
    (models a consumer searching by cuisine on the platform's app)."""
    plat_offers = [o for o in offers if o.platform_id == platform_id]
    if cuisine_filter:
        plat_offers = [o for o in plat_offers if o.cuisine == cuisine_filter]
    scored = sorted(plat_offers, key=lambda o: platform_score(o), reverse=True)
    return scored[:top_n]


# ── LLM ranking ───────────────────────────────────────────────────────────────

# Symmetric 9×9 cuisine similarity table (1.0 = identical, 0.05 = default for unlisted pairs).
# Off-diagonal scores reflect culinary/cultural proximity.
_CUISINE_SIMILARITY: dict = {
    # Self-similarity
    ("Italian",       "Italian"):       1.00,
    ("Chinese",       "Chinese"):       1.00,
    ("Indian",        "Indian"):        1.00,
    ("Mexican",       "Mexican"):       1.00,
    ("Japanese",      "Japanese"):      1.00,
    ("American",      "American"):      1.00,
    ("Thai",          "Thai"):          1.00,
    ("Korean",        "Korean"):        1.00,
    ("Mediterranean", "Mediterranean"): 1.00,
    # East-Asian cluster
    ("Chinese",  "Japanese"): 0.50, ("Japanese", "Chinese"):  0.50,
    ("Chinese",  "Korean"):   0.55, ("Korean",   "Chinese"):  0.55,
    ("Japanese", "Korean"):   0.55, ("Korean",   "Japanese"): 0.55,
    ("Chinese",  "Thai"):     0.40, ("Thai",     "Chinese"):  0.40,
    ("Japanese", "Thai"):     0.35, ("Thai",     "Japanese"): 0.35,
    ("Korean",   "Thai"):     0.35, ("Thai",     "Korean"):   0.35,
    # South/Southeast Asian
    ("Indian",   "Thai"):     0.40, ("Thai",     "Indian"):   0.40,
    ("Indian",   "Mexican"):  0.25, ("Mexican",  "Indian"):   0.25,
    # Western / Mediterranean cluster
    ("Italian",  "Mediterranean"): 0.55, ("Mediterranean", "Italian"):  0.55,
    ("Italian",  "American"): 0.35, ("American", "Italian"):  0.35,
    ("Mediterranean", "American"): 0.25, ("American", "Mediterranean"): 0.25,
    # American / Western crossover
    ("Mexican",  "American"): 0.40, ("American", "Mexican"):  0.40,
    # Broader overlaps
    ("Japanese", "American"): 0.20, ("American", "Japanese"): 0.20,
    ("Chinese",  "American"): 0.15, ("American", "Chinese"):  0.15,
    ("Indian",   "American"): 0.15, ("American", "Indian"):   0.15,
    ("Korean",   "American"): 0.20, ("American", "Korean"):   0.20,
    ("Thai",     "American"): 0.15, ("American", "Thai"):     0.15,
    ("Indian",   "Mediterranean"): 0.20, ("Mediterranean", "Indian"): 0.20,
    # Distant pairings — default handled by .get() fallback of 0.05
    ("Chinese",  "Indian"):   0.20, ("Indian",   "Chinese"):  0.20,
    ("Japanese", "Indian"):   0.15, ("Indian",   "Japanese"): 0.15,
    ("Italian",  "Chinese"):  0.10, ("Chinese",  "Italian"):  0.10,
    ("Italian",  "Indian"):   0.10, ("Indian",   "Italian"):  0.10,
    ("Italian",  "Japanese"): 0.10, ("Japanese", "Italian"):  0.10,
    ("Italian",  "Mexican"):  0.20, ("Mexican",  "Italian"):  0.20,
    ("Chinese",  "Mexican"):  0.10, ("Mexican",  "Chinese"):  0.10,
    ("Japanese", "Mexican"):  0.10, ("Mexican",  "Japanese"): 0.10,
    ("Korean",   "Mexican"):  0.15, ("Mexican",  "Korean"):   0.15,
    ("Thai",     "Mexican"):  0.15, ("Mexican",  "Thai"):     0.15,
    ("Korean",   "Indian"):   0.15, ("Indian",   "Korean"):   0.15,
    ("Mediterranean", "Mexican"): 0.20, ("Mexican", "Mediterranean"): 0.20,
    ("Mediterranean", "Chinese"): 0.10, ("Chinese", "Mediterranean"): 0.10,
    ("Mediterranean", "Japanese"): 0.10, ("Japanese", "Mediterranean"): 0.10,
    ("Mediterranean", "Korean"): 0.10, ("Korean", "Mediterranean"): 0.10,
    ("Mediterranean", "Thai"): 0.15, ("Thai", "Mediterranean"): 0.15,
    ("Italian",  "Korean"):   0.10, ("Korean",   "Italian"):  0.10,
    ("Italian",  "Thai"):     0.10, ("Thai",     "Italian"):  0.10,
}


def _semantic_match(offer: Offer, intent: Intent) -> float:
    """Continuous cuisine similarity score from lookup table (0.0–1.0)."""
    return _CUISINE_SIMILARITY.get((offer.cuisine, intent.cuisine), 0.05)


def _affordability_fit(offer: Offer, intent: Intent) -> float:
    """1.0 if under budget, grades down linearly if over budget."""
    if offer.total_price <= intent.budget:
        return 1.0
    over = offer.total_price - intent.budget
    return max(0.0, 1.0 - over / intent.budget)


def llm_score(offer: Offer,
              intent: Intent,
              platform_sponsorship_bias: float = 0.0,
              weights: Optional[Dict] = None) -> float:
    """
    Score an offer from the LLM's perspective given a consumer intent.
    platform_sponsorship_bias: extra additive term from paid sponsorship.
    """
    w = weights or config.LLM_SCORE_WEIGHTS
    score = (
        w["semantic_match"]    * _semantic_match(offer, intent)
        + w["affordability"]   * _affordability_fit(offer, intent)
        + w["quality"]         * offer.quality / config.QUALITY_SCALE
        - w["neg_delivery_time"] * offer.delivery_time / 90.0
        - w["neg_total_price"] * offer.total_price / 40.0
        + platform_sponsorship_bias   # already scaled by bias_strength in the caller
    )
    return float(score)


def llm_shortlist(offers:       List[Offer],
                  intent:       Intent,
                  platforms:    List[Platform],
                  regime:       str = "neutral",
                  bias_strength: float = None,
                  k:            int = None) -> List[Offer]:
    """
    Return the top-K offers as ranked by the LLM under the given monetisation regime.

    regime options:
        "neutral"  — no sponsorship bias
        "cpc"      — bias proportional to platform's CPC sponsorship payment
        "cpa"      — bias proportional to platform's CPA sponsorship payment
        "cpfi"     — bias proportional to platform's CPFI sponsorship payment
    """
    k = k or config.LLM_K

    weights = None  # use config defaults
    bs = bias_strength if bias_strength is not None else config.SPONSORSHIP_BIAS_STRENGTH

    plat_map  = {p.platform_id: p for p in platforms}
    budgets   = _get_sponsorship_budgets(regime)
    max_spend = max(budgets.values(), default=1.0) or 1.0

    scored = []
    for offer in offers:
        plat      = plat_map[offer.platform_id]
        spend     = budgets.get(plat.name, 0.0)
        norm_bias = spend / max_spend if max_spend > 0 else 0.0
        if regime == "cpfi":
            # Under CPFI, paid bias only helps when the offer is likely to fulfil
            # the user's intent; off-intent sponsored offers have little value.
            bias_term = bs * norm_bias * intent_fulfilment(offer, intent)
        else:
            bias_term = bs * norm_bias if regime != "neutral" else 0.0
        s = llm_score(offer, intent, platform_sponsorship_bias=bias_term, weights=weights)
        scored.append((s, offer))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [o for _, o in scored[:k]]


def _get_sponsorship_budgets(regime: str) -> Dict[str, float]:
    if regime == "cpc":
        return config.LLM_SPONSORSHIP_CPC
    elif regime == "cpa":
        return config.LLM_SPONSORSHIP_CPA
    elif regime == "cpfi":
        return config.LLM_SPONSORSHIP_CPFI
    return {}   # neutral


# ── Shortlist quality metric (for LLM evaluation) ────────────────────────────

def avg_shortlist_relevance(shortlist: List[Offer], intent: Intent) -> float:
    """Average semantic match score in the shortlist (0–1)."""
    if not shortlist:
        return 0.0
    return float(np.mean([_semantic_match(o, intent) for o in shortlist]))
