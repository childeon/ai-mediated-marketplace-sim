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
from typing import List, Optional, Dict, Union
import numpy as np

import config
from entities import (Consumer, Restaurant, Platform, Offer,
                      Intent, build_platforms, build_restaurants,
                      build_offers, build_consumers)
from ranking import rank_offers_by_platform, llm_shortlist, avg_shortlist_relevance
from choice import choose_offer, click_offer, purchase_clicked_offer, intent_fulfilment


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
    clicked:             bool           # LLM world: consumer clicked a recommendation
    clicked_platform_id: Optional[int]   # platform whose recommendation was clicked
    payer_platform_id:   Optional[int]   # platform charged by the LLM, if any
    exposed_restaurant_ids: List[int]     # restaurants shown in feed/shortlist
    exposed_platform_ids:   List[int]     # platforms shown in feed/shortlist
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
    Consumer searches their desired cuisine on their 2 highest-loyalty platforms.
    Each platform returns its top-ranked offers within that cuisine (sponsored
    slots, ratings, promo boosts — but no cross-platform aggregation).
    """
    n_plat  = len(platforms)
    n_check = min(config.CONSUMER_PLATFORMS_INSPECTED, n_plat)

    checked_pids = [
        pid for pid, _ in sorted(
            consumer.platform_loyalty.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:n_check]
    ]

    visible_offers: List[Offer] = []
    for pid in checked_pids:
        top = rank_offers_by_platform(offers, pid, top_n=5,
                                      cuisine_filter=intent.cuisine)
        visible_offers.extend(top)

    chosen, utility = choose_offer(consumer, visible_offers, intent,
                                   from_llm=False, rng=rng)

    return _build_record(consumer, chosen, intent, utility, 0.0,
                         world="no_llm", regime="neutral",
                         n_platforms=n_check, shortlist_rel=0.0, rng=rng,
                         exposed_offers=visible_offers)


# ── World B: LLM ──────────────────────────────────────────────────────────────

def _llm_session(consumer:     Consumer,
                 offers:       List[Offer],
                 platforms:    List[Platform],
                 intent:       Intent,
                 regime:       str,
                 rng:          np.random.Generator,
                 payment_scale: Union[float, Dict] = 1.0) -> OrderRecord:
    """
    Consumer queries LLM. LLM returns top-K shortlist.
    payment_scale: multiply all LLM payments by this factor.
      1.0 = normal; 0.0 = routing bias preserved but LLM earns nothing
      (used for two-pass WTP calibration in experiments).
    """
    shortlist = llm_shortlist(offers, intent, platforms, regime=regime)
    rel       = avg_shortlist_relevance(shortlist, intent)
    clicked, click_utility = click_offer(consumer, shortlist, intent, rng)

    if clicked is None:
        return _build_record(consumer, None, intent, click_utility, 0.0,
                             world="llm", regime=regime,
                             n_platforms=1, shortlist_rel=rel, rng=rng,
                             clicked_offer=None, exposed_offers=shortlist)

    purchased, utility = purchase_clicked_offer(
        consumer, clicked, intent, rng, utility=click_utility
    )
    chosen = clicked if purchased else None

    llm_pay = _compute_llm_payment(clicked, purchased, intent, regime,
                                   payment_scale=payment_scale)

    return _build_record(consumer, chosen, intent, utility, llm_pay,
                         world="llm", regime=regime,
                         n_platforms=1, shortlist_rel=rel, rng=rng,
                         clicked_offer=clicked, exposed_offers=shortlist)


def _compute_llm_payment(clicked:       Optional[Offer],
                          purchased:    bool,
                          intent:       Intent,
                          regime:       str,
                          payment_scale: Union[float, Dict] = 1.0) -> float:
    """LLM earnings under the given regime, scaled by payment_scale."""
    if regime == "neutral" or clicked is None or payment_scale == 0.0:
        return 0.0

    budgets = {
        "cpc":  config.LLM_SPONSORSHIP_CPC,
        "cpa":  config.LLM_SPONSORSHIP_CPA,
        "cpfi": config.LLM_SPONSORSHIP_CPFI,
    }
    rate_map = budgets.get(regime, {})
    rate     = rate_map.get(clicked.platform_name, 0.0) * _payment_scale_for_offer(
        payment_scale, clicked
    )

    if regime == "cpc":
        return rate
    elif regime == "cpa":
        return rate if purchased else 0.0
    elif regime == "cpfi":
        return rate * intent_fulfilment(clicked, intent) if purchased else 0.0

    return 0.0


def _payment_scale_for_offer(payment_scale: Union[float, Dict],
                             offer: Offer) -> float:
    if isinstance(payment_scale, dict):
        return float(
            payment_scale.get(offer.platform_id,
                              payment_scale.get(offer.platform_name, 0.0))
        )
    return float(payment_scale)


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
                  rng:         np.random.Generator,
                  clicked_offer: Optional[Offer] = None,
                  exposed_offers: Optional[List[Offer]] = None) -> OrderRecord:
    exposed_offers = exposed_offers or []
    exposed_restaurant_ids = sorted({o.restaurant_id for o in exposed_offers})
    exposed_platform_ids = sorted({o.platform_id for o in exposed_offers})

    if chosen is None:
        clicked = clicked_offer is not None
        payer_platform_id = clicked_offer.platform_id if llm_pay > 0.0 and clicked_offer else None
        return OrderRecord(
            consumer_id=consumer.consumer_id,
            restaurant_id=None, platform_id=None,
            purchased=False,
            cuisine_requested=intent.cuisine, cuisine_delivered=None,
            total_price=0.0, delivery_time=0,
            intent_fulfilment=0.0, consumer_utility=utility,
            restaurant_profit=0.0, platform_commission=0.0,
            platform_delivery_fee=0.0, platform_net=-llm_pay,
            llm_payment=llm_pay,
            clicked=clicked,
            clicked_platform_id=clicked_offer.platform_id if clicked_offer else None,
            payer_platform_id=payer_platform_id,
            exposed_restaurant_ids=exposed_restaurant_ids,
            exposed_platform_ids=exposed_platform_ids,
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
                       - chosen.menu_price * chosen.cost_ratio
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
        clicked=clicked_offer is not None,
        clicked_platform_id=clicked_offer.platform_id if clicked_offer else None,
        payer_platform_id=chosen.platform_id if llm_pay > 0.0 else None,
        exposed_restaurant_ids=exposed_restaurant_ids,
        exposed_platform_ids=exposed_platform_ids,
        world=world, regime=regime,
        n_platforms_checked=n_platforms,
        shortlist_relevance=shortlist_rel,
    )


# ── Main simulation run ────────────────────────────────────────────────────────

def run_simulation(world:          str   = "no_llm",
                   regime:         str   = "neutral",
                   seed:           int   = None,
                   verbose:        bool  = False,
                   payment_scale:  Union[float, Dict] = 1.0) -> List[OrderRecord]:
    """
    Run one full simulation pass (N_CONSUMERS consumers) in the given world/regime.
    payment_scale: scales LLM payments without affecting routing bias (used for
    two-pass WTP calibration — set to 0.0 to measure gross platform surplus).
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
            rec = _llm_session(consumer, offers, platforms, intent, regime, rng,
                               payment_scale=payment_scale)

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
