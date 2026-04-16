"""
entities.py — Dataclasses for Consumer, Restaurant, Platform, and Offer.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import config


# ── Platform ───────────────────────────────────────────────────────────────────

@dataclass
class Platform:
    platform_id:    int
    name:           str
    commission:     float         # fraction of menu price
    delivery_fee_range: tuple
    subsidy_budget: float
    sponsorship_payment: float = 0.0   # payment to LLM per event (set by regime)

    def delivery_fee(self, rng: np.random.Generator) -> float:
        lo, hi = self.delivery_fee_range
        return float(rng.uniform(lo, hi))

    def __repr__(self):
        return f"Platform({self.name})"


# ── Restaurant ─────────────────────────────────────────────────────────────────

@dataclass
class Restaurant:
    restaurant_id: int
    name:          str
    cuisine:       str
    quality:       float          # 0–1
    base_price:    float          # menu price ($)
    prep_time:     int            # minutes (restaurant-side)
    cost_ratio:    float          # production cost fraction
    platform_ids:  List[int]      = field(default_factory=list)
    promo_budget:  Dict[int, float] = field(default_factory=dict)  # {platform_id: $/order}

    @property
    def production_cost(self) -> float:
        return self.base_price * self.cost_ratio

    def __repr__(self):
        return f"Restaurant({self.name}, {self.cuisine})"


# ── Offer ──────────────────────────────────────────────────────────────────────

@dataclass
class Offer:
    offer_id:         int
    restaurant_id:    int
    platform_id:      int
    cuisine:          str
    menu_price:       float
    delivery_fee:     float
    delivery_time:    int          # total minutes (prep + platform logistics)
    quality:          float
    promo_discount:   float        # $ discount funded by platform/restaurant promo
    sponsored_boost:  float        # internal platform ad boost [0–1]
    platform_name:    str
    restaurant_name:  str

    @property
    def total_price(self) -> float:
        return max(0.0, self.menu_price + self.delivery_fee - self.promo_discount)

    def __repr__(self):
        return (f"Offer({self.restaurant_name}@{self.platform_name} "
                f"${self.total_price:.2f} {self.delivery_time}min)")


# ── Consumer ───────────────────────────────────────────────────────────────────

@dataclass
class Intent:
    cuisine:      str
    budget:       float
    max_time:     int             # minutes

@dataclass
class Consumer:
    consumer_id:       int
    preferred_cuisines: List[str]     # ordered preference
    budget:            float
    max_delivery_time: int
    price_sensitivity: float          # higher = more price-averse
    time_sensitivity:  float
    quality_sensitivity: float
    llm_trust:         float          # 0–1
    platform_loyalty:  Dict[int, float]  # {platform_id: loyalty score 0–1}

    def sample_intent(self, rng: np.random.Generator) -> Intent:
        """Draw a cuisine need weighted by preference, with budget/time from consumer profile."""
        cuisine = rng.choice(self.preferred_cuisines)
        # Allow a little slack so the sim isn't overly strict
        budget    = self.budget * rng.uniform(0.9, 1.0)
        max_time  = int(self.max_delivery_time * rng.uniform(0.9, 1.1))
        return Intent(cuisine=cuisine, budget=budget, max_time=max_time)

    def __repr__(self):
        return f"Consumer({self.consumer_id}, budget=${self.budget:.0f})"


# ── Factory helpers ────────────────────────────────────────────────────────────

def build_platforms(rng: np.random.Generator) -> List[Platform]:
    platforms = []
    for pid, p in enumerate(config.PLATFORM_PARAMS):
        platforms.append(Platform(
            platform_id=pid,
            name=p["name"],
            commission=p["commission"],
            delivery_fee_range=p["delivery_fee_range"],
            subsidy_budget=p["subsidy_budget"],
        ))
    return platforms


def build_restaurants(platforms: List[Platform], rng: np.random.Generator) -> List[Restaurant]:
    restaurants = []
    n_plat = len(platforms)
    for rid in range(config.N_RESTAURANTS):
        cuisine   = rng.choice(config.CUISINES)
        quality   = float(rng.uniform(*config.RESTAURANT_QUALITY_RANGE))
        price     = float(rng.uniform(*config.RESTAURANT_PRICE_RANGE))
        prep      = int(rng.integers(*config.RESTAURANT_PREP_TIME_RANGE))
        cost_rat  = float(rng.uniform(*config.RESTAURANT_COST_RATIO_RANGE))

        n_join    = int(rng.integers(1, config.MAX_PLATFORMS_PER_RESTAURANT + 1))
        pids      = list(rng.choice(n_plat, size=n_join, replace=False))
        promo     = {pid: float(rng.uniform(*config.RESTAURANT_PROMO_RANGE)) for pid in pids}

        restaurants.append(Restaurant(
            restaurant_id=rid,
            name=f"R{rid:03d}_{cuisine[:3]}",
            cuisine=cuisine,
            quality=quality,
            base_price=price,
            prep_time=prep,
            cost_ratio=cost_rat,
            platform_ids=pids,
            promo_budget=promo,
        ))
    return restaurants


def build_offers(restaurants: List[Restaurant],
                 platforms:   List[Platform],
                 rng:         np.random.Generator) -> List[Offer]:
    offers = []
    offer_id = 0
    plat_map = {p.platform_id: p for p in platforms}

    for r in restaurants:
        for pid in r.platform_ids:
            plat = plat_map[pid]
            dfee      = plat.delivery_fee(rng)
            # Platform delivery time = prep + logistics component
            logistics = int(rng.integers(10, 35))
            dtime     = r.prep_time + logistics
            promo_d   = min(r.promo_budget.get(pid, 0.0), dfee * 0.8)  # cap discount
            sponsored = float(rng.uniform(0.0, 0.5))  # platform internal ad boost

            offers.append(Offer(
                offer_id=offer_id,
                restaurant_id=r.restaurant_id,
                platform_id=pid,
                cuisine=r.cuisine,
                menu_price=r.base_price,
                delivery_fee=dfee,
                delivery_time=dtime,
                quality=r.quality,
                promo_discount=promo_d,
                sponsored_boost=sponsored,
                platform_name=plat.name,
                restaurant_name=r.name,
            ))
            offer_id += 1
    return offers


def build_consumers(platforms: List[Platform], rng: np.random.Generator) -> List[Consumer]:
    consumers = []
    n_plat = len(platforms)
    for cid in range(config.N_CONSUMERS):
        # Each consumer has an ordered cuisine preference (2–4 cuisines)
        n_pref   = int(rng.integers(2, 5))
        cuisines = list(rng.choice(config.CUISINES, size=n_pref, replace=False))

        budget   = float(rng.uniform(*config.CONSUMER_BUDGET_RANGE))
        max_time = int(rng.integers(*config.CONSUMER_MAX_DELIVERY_RANGE))
        p_sens   = abs(float(rng.normal(1.0, 0.3)))
        t_sens   = abs(float(rng.normal(0.8, 0.3)))
        q_sens   = abs(float(rng.normal(1.0, 0.3)))
        trust    = float(rng.uniform(*config.CONSUMER_LLM_TRUST_RANGE))
        loyalty  = {pid: float(rng.uniform(0, 1)) for pid in range(n_plat)}

        consumers.append(Consumer(
            consumer_id=cid,
            preferred_cuisines=cuisines,
            budget=budget,
            max_delivery_time=max_time,
            price_sensitivity=p_sens,
            time_sensitivity=t_sens,
            quality_sensitivity=q_sens,
            llm_trust=trust,
            platform_loyalty=loyalty,
        ))
    return consumers
