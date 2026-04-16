"""
simulation.py — Core simulation engine.

Supports two worlds:
    "no_llm"  — consumers search platforms directly (fragmented search)
    "llm"     — consumers query an LLM that aggregates and ranks offers

And four LLM monetisation regimes:
    "neutral", "cpc", "cpa", "cpfi"
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import numpy as np

import config
from entities import (Consumer, Restaurant, Platform, Offer,
                      Intent, build_platforms, build_restaurants,
                      build_offers, build_consumers)
from ranking import rank_offers_by_platform, llm_shortlist, avg_shortlist_relevance
from choice import choose_offer, intent_fulfilment


# ── Per-order record ──────────────────────────────────────────────────────────

@dataclass
class OrderRecord:
    consumer_id:         int
    restaurant_id:       Optional[int]
    platform_id:         Optional[int]
    purchased:           bool
    cuisine_requested:   str
    cuisine_delivered:   Optional[str]
    total_price:         float
    delivery_time:       int
    intent_fulfilment:   float
    consumer_utility:    float
    restaurant_profit:   float
    platform_commission: float
    platform_delivery_fee: float
    platform_net:        float          # commission + delivery_fee - subsidy_spend - llm_payment
    llm_payment:         float          # payment LLM received for this order
    world:               str
    regime:              str
    n_platforms_checked: int            # no-LLM world: how many platforms inspected
    shortlist_relevance: float          # LLM world: avg relevance of shortlist shown


# ── World A: No-LLM ────────────────────────────────────────────────────────────

def _no_llm_session(consumer:  Consumer,
                    offers:    List[Offer],
                    platforms: List[Platform],
                    intent:    Intent,
                    rng:       np.random.Generator) -> OrderRecord:
    """
    Consumer inspects a random subset of platforms and sees top offers from each.
    """
    n_plat = len(platforms)
    n_check = min(config.CONSUMER_PLATFORMS_INSPECTED, n_plat)
    checked_pids = list(rng.choice(n_plat, size=n_check, replace=False))

    # Collect top-5 offers per checked platform (already sorted by platform score)
    visible_offers: List[Offer] = []
    for pid in checked_pids:
        top = rank_offers_by_platform(offers, pid, top_n=5)
        visible_offers.extend(top)

    chosen, utility = choose_offer(consumer, visible_offers, intent,
                                   from_llm=False, rng=rng)

    return _build_record(consumer, chosen, intent, utility, 0.0,
                         world="no_llm", regime="neutral",
                         n_platforms=n_check, shortlist_rel=0.0, rng=rng)


# ── World B: LLM ──────────────────────────────────────────────────────────────

def _llm_session(consumer:  Consumer,
                 offers:    List[Offer],
                 platforms: List[Platform],
                 intent:    Intent,
                 regime:    str,
                 rng:       np.random.Generator) -> OrderRecord:
    """
    Consumer queries LLM. LLM returns top-K shortlist.
    Consumer chooses from shortlist (possibly no-purchase).
    """
    shortlist = llm_shortlist(offers, intent, platforms, regime=regime)
    rel       = avg_shortlist_relevance(shortlist, intent)
    chosen, utility = choose_offer(consumer, shortlist, intent,
                                   from_llm=True, rng=rng)

    # Compute LLM payment based on regime
    llm_pay = _compute_llm_payment(chosen, shortlist, intent, regime)

    return _build_record(consumer, chosen, intent, utility, llm_pay,
                         world="llm", regime=regime,
                         n_platforms=1, shortlist_rel=rel, rng=rng)


def _compute_llm_payment(chosen: Optional[Offer],
                          shortlist: List[Offer],
                          intent: Intent,
                          regime: str) -> float:
    """Calculate how much the LLM earns under the given monetisation regime."""
    if regime == "neutral" or chosen is None:
        return 0.0

    budgets = {
        "cpc":  config.LLM_SPONSORSHIP_CPC,
        "cpa":  config.LLM_SPONSORSHIP_CPA,
        "cpfi": config.LLM_SPONSORSHIP_CPFI,
    }
    rate_map = budgets.get(regime, {})
    rate     = rate_map.get(chosen.platform_name, 0.0)

    if regime == "cpc":
        # Pay per click-through (treat any shown offer as potential click; here per purchase)
        return rate

    elif regime == "cpa":
        # Pay per completed order
        return rate

    elif regime == "cpfi":
        # Pay only if intent fulfilled
        fi = intent_fulfilment(chosen, intent)
        return rate * fi

    return 0.0


# ── Record builder ─────────────────────────────────────────────────────────────

def _build_record(consumer:    Consumer,
                  chosen:      Optional[Offer],
                  intent:      Intent,
                  utility:     float,
                  llm_pay:     float,
                  world:       str,
                  regime:      str,
                  n_platforms: int,
                  shortlist_rel: float,
                  rng:         np.random.Generator) -> OrderRecord:
    if chosen is None:
        return OrderRecord(
            consumer_id=consumer.consumer_id,
            restaurant_id=None, platform_id=None,
            purchased=False,
            cuisine_requested=intent.cuisine, cuisine_delivered=None,
            total_price=0.0, delivery_time=0,
            intent_fulfilment=0.0, consumer_utility=utility,
            restaurant_profit=0.0, platform_commission=0.0,
            platform_delivery_fee=0.0, platform_net=0.0,
            llm_payment=0.0,
            world=world, regime=regime,
            n_platforms_checked=n_platforms,
            shortlist_relevance=shortlist_rel,
        )

    # Find platform commission rate (we stored it in config; look it up from PLATFORM_PARAMS)
    commission_rate = config.PLATFORM_PARAMS[chosen.platform_id]["commission"]
    commission      = chosen.menu_price * commission_rate
    delivery_rev    = chosen.delivery_fee
    # Simplified: subsidy is baked into promo_discount; platform spent that
    subsidy_spend   = chosen.promo_discount * 0.5  # rough: assume 50% funded by platform
    platform_net    = commission + delivery_rev - subsidy_spend - llm_pay

    rest_profit     = (chosen.menu_price
                       - chosen.menu_price * config.RESTAURANT_COST_RATIO_RANGE[0]  # approx
                       - commission)
    fi              = intent_fulfilment(chosen, intent)

    return OrderRecord(
        consumer_id=consumer.consumer_id,
        restaurant_id=chosen.restaurant_id, platform_id=chosen.platform_id,
        purchased=True,
        cuisine_requested=intent.cuisine, cuisine_delivered=chosen.cuisine,
        total_price=chosen.total_price, delivery_time=chosen.delivery_time,
        intent_fulfilment=fi, consumer_utility=utility,
        restaurant_profit=rest_profit, platform_commission=commission,
        platform_delivery_fee=delivery_rev, platform_net=platform_net,
        llm_payment=llm_pay,
        world=world, regime=regime,
        n_platforms_checked=n_platforms,
        shortlist_relevance=shortlist_rel,
    )


# ── Main simulation run ────────────────────────────────────────────────────────

def run_simulation(world:   str  = "no_llm",
                   regime:  str  = "neutral",
                   seed:    int  = None,
                   verbose: bool = False) -> List[OrderRecord]:
    """
    Run one full simulation pass (N_CONSUMERS consumers) in the given world/regime.
    Returns a list of OrderRecord objects.
    """
    seed = seed if seed is not None else config.SEED
    rng  = np.random.default_rng(seed)

    platforms   = build_platforms(rng)
    restaurants = build_restaurants(platforms, rng)
    offers      = build_offers(restaurants, platforms, rng)
    consumers   = build_consumers(platforms, rng)

    records = []
    for consumer in consumers:
        intent = consumer.sample_intent(rng)

        if world == "no_llm":
            rec = _no_llm_session(consumer, offers, platforms, intent, rng)
        else:
            rec = _llm_session(consumer, offers, platforms, intent, regime, rng)

        records.append(rec)

        if verbose and consumer.consumer_id < 3:
            _print_sample(consumer, intent, rec)

    return records


def _print_sample(consumer: Consumer, intent: Intent, rec: OrderRecord):
    print(f"\n[Consumer {consumer.consumer_id}] intent={intent.cuisine} "
          f"budget=${intent.budget:.2f} max_time={intent.max_time}min")
    if rec.purchased:
        print(f"  -> Ordered from R{rec.restaurant_id} on P{rec.platform_id} "
              f"price=${rec.total_price:.2f} time={rec.delivery_time}min "
              f"fi={rec.intent_fulfilment:.2f} utility={rec.consumer_utility:.2f}")
    else:
        print(f"  -> No purchase (utility={rec.consumer_utility:.2f})")
