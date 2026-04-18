"""
ranking.py — Platform-internal scoring and LLM scoring functions.
All weights come from config so experiments can override them.
"""

from __future__ import annotations
from typing import List, Dict, Optional
import numpy as np

import config
from entities import Offer, Consumer, Intent, Platform


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
        - w["neg_total_price"] * offer.total_price / 40.0
        - w["neg_delivery_time"] * offer.delivery_time / 90.0
        + w["promo_boost"]     * (offer.promo_discount / 5.0)
        + w["sponsored_boost"] * offer.sponsored_boost
    )
    return float(score)


def rank_offers_by_platform(offers: List[Offer],
                             platform_id: int,
                             top_n: int = 20) -> List[Offer]:
    """Return top_n offers for a given platform, sorted by platform score."""
    plat_offers = [o for o in offers if o.platform_id == platform_id]
    scored = sorted(plat_offers, key=lambda o: platform_score(o), reverse=True)
    return scored[:top_n]


# ── LLM ranking ───────────────────────────────────────────────────────────────

# Symmetric 6×6 cuisine similarity table (1.0 = identical, 0.0 = no overlap).
# Off-diagonal scores reflect culinary/cultural proximity.
_CUISINE_SIMILARITY: dict = {
    ("Italian",  "Italian"):  1.00,
    ("Chinese",  "Chinese"):  1.00,
    ("Indian",   "Indian"):   1.00,
    ("Mexican",  "Mexican"):  1.00,
    ("Japanese", "Japanese"): 1.00,
    ("American", "American"): 1.00,
    # East-Asian cluster
    ("Chinese",  "Japanese"): 0.50, ("Japanese", "Chinese"):  0.50,
    # American / Western crossover
    ("Mexican",  "American"): 0.40, ("American", "Mexican"):  0.40,
    ("Italian",  "American"): 0.35, ("American", "Italian"):  0.35,
    # Bold/spiced overlap
    ("Indian",   "Mexican"):  0.25, ("Mexican",  "Indian"):   0.25,
    # Broader Asian overlap
    ("Chinese",  "Indian"):   0.20, ("Indian",   "Chinese"):  0.20,
    ("Japanese", "American"): 0.20, ("American", "Japanese"): 0.20,
    ("Italian",  "Mexican"):  0.20, ("Mexican",  "Italian"):  0.20,
    # Distant pairings
    ("Chinese",  "American"): 0.15, ("American", "Chinese"):  0.15,
    ("Indian",   "American"): 0.15, ("American", "Indian"):   0.15,
    ("Japanese", "Indian"):   0.15, ("Indian",   "Japanese"): 0.15,
    # Least similar
    ("Italian",  "Chinese"):  0.10, ("Chinese",  "Italian"):  0.10,
    ("Italian",  "Indian"):   0.10, ("Indian",   "Italian"):  0.10,
    ("Italian",  "Japanese"): 0.10, ("Japanese", "Italian"):  0.10,
    ("Chinese",  "Mexican"):  0.10, ("Mexican",  "Chinese"):  0.10,
    ("Japanese", "Mexican"):  0.10, ("Mexican",  "Japanese"): 0.10,
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
    bs = bias_strength if bias_strength is not None else config.SPONSORSHIP_BIAS_STRENGTH

    plat_map  = {p.platform_id: p for p in platforms}
    budgets   = _get_sponsorship_budgets(regime)
    max_spend = max(budgets.values(), default=1.0) or 1.0

    scored = []
    for offer in offers:
        plat      = plat_map[offer.platform_id]
        spend     = budgets.get(plat.name, 0.0)
        norm_bias = spend / max_spend if max_spend > 0 else 0.0
        bias_term = bs * norm_bias if regime != "neutral" else 0.0
        s = llm_score(offer, intent, platform_sponsorship_bias=bias_term)
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
