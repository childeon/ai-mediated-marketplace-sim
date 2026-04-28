"""
choice.py — Consumer utility model and choice functions.
Supports multinomial logit (default) and deterministic argmax.
"""

from __future__ import annotations
from typing import List, Optional, Tuple
import numpy as np

import config
from entities import Consumer, Intent, Offer


# ── Intent fulfilment ─────────────────────────────────────────────────────────

def intent_fulfilment(offer: Offer, intent: Intent) -> float:
    """
    Graded score 0–1: how well an offer satisfies the consumer's stated intent.
    Penalised for wrong cuisine (hard zero), over-budget, over-time, and low quality.
    Quality scales from 0.60 (2★) to 1.00 (5★) — platform-promoted sponsored
    restaurants may be lower-rated than what an intent-matched LLM would surface.
    """
    score = 1.0

    # Cuisine: hard zero for mismatch
    if offer.cuisine != intent.cuisine:
        score *= 0.0

    # Price: graded penalty for overage relative to budget
    if offer.total_price > intent.budget:
        over = offer.total_price - intent.budget
        score *= max(0.0, 1.0 - config.INTENT_PRICE_PENALTY * over / intent.budget)

    # Time: graded penalty per minute over tolerance
    if offer.delivery_time > intent.max_time:
        over = offer.delivery_time - intent.max_time
        score *= max(0.0, 1.0 - config.INTENT_TIME_PENALTY * over)

    # Quality: scales fi from (1 - INTENT_QUALITY_WEIGHT) at min stars to 1.0 at max stars
    q_min = config.RESTAURANT_QUALITY_RANGE[0]
    q_max = config.RESTAURANT_QUALITY_RANGE[1]
    q_norm = (offer.quality - q_min) / (q_max - q_min)   # 0.0 at 2★, 1.0 at 5★
    quality_factor = (1.0 - config.INTENT_QUALITY_WEIGHT) + config.INTENT_QUALITY_WEIGHT * q_norm
    score *= quality_factor

    return float(score)


# ── Utility ───────────────────────────────────────────────────────────────────

def consumer_utility(consumer:      Consumer,
                     offer:         Offer,
                     intent:        Intent,
                     from_llm:      bool,
                     rng:           np.random.Generator,
                     weights:       Optional[dict] = None) -> float:
    """
    Compute consumer utility for a given offer.
    Incorporates preference match, price/time sensitivity, LLM trust, and noise.
    """
    w = weights or config.UTILITY_WEIGHTS

    cuisine_match = 1.0 if offer.cuisine == intent.cuisine else 0.0
    norm_price    = offer.total_price / 40.0          # rough normalisation
    norm_time     = offer.delivery_time / 90.0
    promo_val     = offer.promo_discount / 5.0
    loyalty       = consumer.platform_loyalty.get(offer.platform_id, 0.0)
    llm_bonus     = consumer.llm_trust if from_llm else 0.0
    noise         = float(rng.normal(0, w["noise_scale"]))

    utility = (
        w["cuisine_match"]   * cuisine_match
        + w["quality"]       * consumer.quality_sensitivity * offer.quality / config.QUALITY_SCALE
        - w["neg_total_price"] * consumer.price_sensitivity * norm_price
        - w["neg_delivery_time"] * consumer.time_sensitivity * norm_time
        + w["promo_value"]   * promo_val
        + w["llm_trust_bonus"] * llm_bonus * cuisine_match   # bonus only if relevant
        + w["platform_loyalty"] * loyalty
        + noise
    )
    return float(utility)


# ── Choice models ─────────────────────────────────────────────────────────────

def logit_choice(utilities: List[float],
                 rng:       np.random.Generator) -> int:
    """
    Multinomial logit over a list of utilities (including outside option appended last).
    Returns the index of the chosen option (-1 for no purchase if outside option is last).
    """
    u = np.array(utilities, dtype=float)
    # Subtract max for numerical stability
    u -= u.max()
    exp_u = np.exp(u)
    probs = exp_u / exp_u.sum()
    idx = int(rng.choice(len(utilities), p=probs))
    return idx


def deterministic_choice(utilities: List[float]) -> int:
    """Choose highest utility; last element is outside option."""
    best = int(np.argmax(utilities))
    return best


def choose_offer(consumer:     Consumer,
                 offers:       List[Offer],
                 intent:       Intent,
                 from_llm:     bool,
                 rng:          np.random.Generator) -> Tuple[Optional[Offer], float]:
    """
    Given a set of observed offers, select one using the configured choice model.
    Returns (chosen_offer_or_None, utility).
    None means no purchase (outside option chosen).
    """
    if not offers:
        return None, config.NO_PURCHASE_UTILITY

    utilities = [
        consumer_utility(consumer, o, intent, from_llm, rng) for o in offers
    ]
    # Append no-purchase outside option
    utilities.append(config.NO_PURCHASE_UTILITY)

    if config.CHOICE_MODEL == "logit":
        idx = logit_choice(utilities, rng)
    else:
        idx = deterministic_choice(utilities)

    if idx == len(offers):   # outside option
        return None, config.NO_PURCHASE_UTILITY

    chosen = offers[idx]
    return chosen, utilities[idx]


def click_offer(consumer: Consumer,
                offers:   List[Offer],
                intent:   Intent,
                rng:      np.random.Generator) -> Tuple[Optional[Offer], float]:
    """
    First-stage LLM interaction: consumer clicks/selects one recommendation from
    the shortlist, or ignores the shortlist. This is less committal than purchase.
    """
    if not offers:
        return None, config.NO_CLICK_UTILITY

    utilities = [
        consumer_utility(consumer, o, intent, from_llm=True, rng=rng) for o in offers
    ]
    utilities.append(config.NO_CLICK_UTILITY)

    if config.CHOICE_MODEL == "logit":
        idx = logit_choice(utilities, rng)
    else:
        idx = deterministic_choice(utilities)

    if idx == len(offers):
        return None, config.NO_CLICK_UTILITY

    clicked = offers[idx]
    return clicked, utilities[idx]


def purchase_clicked_offer(consumer: Consumer,
                           offer:    Offer,
                           intent:   Intent,
                           rng:      np.random.Generator,
                           utility:  Optional[float] = None) -> Tuple[bool, float]:
    """
    Second-stage LLM interaction: after clicking into one recommendation, decide
    whether to complete the order. CPA/CPFI bill only if this stage succeeds.
    """
    utility = (
        utility if utility is not None
        else consumer_utility(consumer, offer, intent, from_llm=True, rng=rng)
    )

    if config.CHOICE_MODEL == "logit":
        idx = logit_choice([utility, config.POST_CLICK_NO_PURCHASE_UTILITY], rng)
        return idx == 0, utility if idx == 0 else config.POST_CLICK_NO_PURCHASE_UTILITY

    purchased = utility >= config.POST_CLICK_NO_PURCHASE_UTILITY
    return purchased, utility if purchased else config.POST_CLICK_NO_PURCHASE_UTILITY
