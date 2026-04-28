"""
attribution.py — Optional counterfactual attribution module.

For a sample of completed orders, estimates the marginal contribution of:
  1. LLM sponsorship bias
  2. The LLM itself (vs no-LLM)
  3. Platform promo discounts

Method: simple counterfactual — re-score/re-rank under altered conditions
and compute the change in conversion probability for that consumer's intent.
"""

from __future__ import annotations
from typing import List, Dict, Optional
import numpy as np
import pandas as pd

import config
from entities import (Consumer, Platform, Offer, Intent,
                      build_platforms, build_restaurants,
                      build_offers, build_consumers)
from ranking import llm_shortlist, rank_offers_by_platform
from choice import choose_offer, consumer_utility
from simulation import OrderRecord, _llm_session, _no_llm_session


def _conversion_prob_llm(consumer:  Consumer,
                          offers:    List[Offer],
                          platforms: List[Platform],
                          intent:    Intent,
                          regime:    str,
                          rng:       np.random.Generator,
                          n_samples: int = 50) -> float:
    """Estimate P(purchase) via Monte Carlo under given LLM regime."""
    purchases = 0
    for _ in range(n_samples):
        rec = _llm_session(consumer, offers, platforms, intent, regime, rng)
        if rec.purchased:
            purchases += 1
    return purchases / n_samples


def _conversion_prob_nollm(consumer:  Consumer,
                            offers:    List[Offer],
                            platforms: List[Platform],
                            intent:    Intent,
                            rng:       np.random.Generator,
                            n_samples: int = 50) -> float:
    """Estimate P(purchase) via Monte Carlo without LLM."""
    purchases = 0
    for _ in range(n_samples):
        rec = _no_llm_session(consumer, offers, platforms, intent, rng)
        if rec.purchased:
            purchases += 1
    return purchases / n_samples


def run_attribution(n_consumers:  int = 30,
                    regime:       str = "cpc",
                    n_samples:    int = 50,
                    seed:         int = None) -> pd.DataFrame:
    """
    For a small sample of consumers, compute counterfactual attribution.
    Returns a DataFrame with one row per consumer.
    """
    seed = seed or config.SEED
    rng  = np.random.default_rng(seed)

    platforms   = build_platforms(rng)
    restaurants = build_restaurants(platforms, rng)
    offers      = build_offers(restaurants, platforms, rng)
    consumers   = build_consumers(platforms, rng)[:n_consumers]

    rows = []
    for consumer in consumers:
        intent = consumer.sample_intent(rng)

        # Baseline: actual world with sponsorship
        p_actual = _conversion_prob_llm(
            consumer, offers, platforms, intent, regime, rng, n_samples)

        # Counterfactual A: LLM with no sponsorship bias
        orig_bs = config.SPONSORSHIP_BIAS_STRENGTH
        config.SPONSORSHIP_BIAS_STRENGTH = 0.0
        p_no_bias = _conversion_prob_llm(
            consumer, offers, platforms, intent, "neutral", rng, n_samples)
        config.SPONSORSHIP_BIAS_STRENGTH = orig_bs

        # Counterfactual B: No LLM at all
        p_no_llm = _conversion_prob_nollm(
            consumer, offers, platforms, intent, rng, n_samples)

        # Counterfactual C: LLM + no promo discounts
        zeroed_offers = [
            Offer(
                offer_id=o.offer_id,
                restaurant_id=o.restaurant_id,
                platform_id=o.platform_id,
                cuisine=o.cuisine,
                menu_price=o.menu_price,
                delivery_fee=o.delivery_fee,
                delivery_time=o.delivery_time,
                quality=o.quality,
                cost_ratio=o.cost_ratio,
                promo_discount=0.0,          # <-- zero out promos
                sponsored_boost=o.sponsored_boost,
                platform_name=o.platform_name,
                restaurant_name=o.restaurant_name,
            )
            for o in offers
        ]
        p_no_promo = _conversion_prob_llm(
            consumer, zeroed_offers, platforms, intent, regime, rng, n_samples)

        rows.append({
            "consumer_id":              consumer.consumer_id,
            "cuisine":                  intent.cuisine,
            "budget":                   intent.budget,
            "llm_trust":                consumer.llm_trust,
            "p_actual":                 p_actual,
            "p_no_sponsorship_bias":    p_no_bias,
            "p_no_llm":                 p_no_llm,
            "p_no_promo":               p_no_promo,
            "marginal_bias_effect":     p_actual - p_no_bias,
            "marginal_llm_effect":      p_actual - p_no_llm,
            "marginal_promo_effect":    p_actual - p_no_promo,
        })

    df = pd.DataFrame(rows)
    print("\n=== Attribution Summary ===")
    print(df[["marginal_bias_effect",
              "marginal_llm_effect",
              "marginal_promo_effect"]].describe().round(4))
    return df
