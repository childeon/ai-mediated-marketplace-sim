"""
config.py — Simulation parameters and hyperweights.
All scoring weights and regime flags live here so experiments can override them.
"""

import numpy as np

# ── Reproducibility ────────────────────────────────────────────────────────────
SEED = 42

# ── Scale ─────────────────────────────────────────────────────────────────────
N_PLATFORMS   = 3
N_RESTAURANTS = 50
N_CONSUMERS   = 1000
N_RUNS        = 10          # Monte Carlo iterations per experiment
LLM_K         = 5           # shortlist size

# ── Cuisine categories ─────────────────────────────────────────────────────────
CUISINES = ["Italian", "Chinese", "Indian", "Mexican", "Japanese", "American"]

# ── Platform parameters ────────────────────────────────────────────────────────
PLATFORM_PARAMS = [
    {"name": "QuickEats",  "commission": 0.20, "delivery_fee_range": (2.0, 5.0), "subsidy_budget": 5000, "logistics_time_range": (10, 25)},
    {"name": "FoodRush",   "commission": 0.25, "delivery_fee_range": (1.0, 4.0), "subsidy_budget": 8000, "logistics_time_range": (15, 30)},
    {"name": "NomNom",     "commission": 0.15, "delivery_fee_range": (3.0, 8.0), "subsidy_budget": 3000, "logistics_time_range": (20, 35)},
]

# Per-order sponsorship payment FROM platforms TO LLM under each mechanism.
# Overridden per experiment; None means regime disabled.
LLM_SPONSORSHIP_CPC  = {"QuickEats": 0.50, "FoodRush": 0.80, "NomNom": 0.30}  # per click
LLM_SPONSORSHIP_CPA  = {"QuickEats": 1.50, "FoodRush": 2.00, "NomNom": 1.00}  # per order
LLM_SPONSORSHIP_CPFI = {"QuickEats": 2.00, "FoodRush": 2.50, "NomNom": 1.50}  # per fulfilled intent

# ── Restaurant parameters ──────────────────────────────────────────────────────
RESTAURANT_QUALITY_RANGE    = (2.0, 5.0)   # star ratings displayed as 1–5 ★ (half-star precision)
QUALITY_SCALE               = 5.0           # divide by this to normalise quality to [0, 1] internally
RESTAURANT_PRICE_RANGE      = (10.0, 35.0)
RESTAURANT_PREP_TIME_RANGE  = (5, 25)    # minutes (restaurant-side component)
RESTAURANT_COST_RATIO_RANGE = (0.30, 0.60)   # production cost as fraction of menu price
MAX_PLATFORMS_PER_RESTAURANT = 3

# Platform-specific promo spend per restaurant (drawn at setup)
RESTAURANT_PROMO_RANGE = (0.0, 3.0)    # $ per order equivalent

# ── Consumer parameters ────────────────────────────────────────────────────────
CONSUMER_BUDGET_RANGE           = (15.0, 40.0)
CONSUMER_MAX_DELIVERY_RANGE     = (20, 60)   # minutes
CONSUMER_LLM_TRUST_RANGE        = (0.0, 1.0)
CONSUMER_SEARCH_COST            = 0.5        # disutility per additional platform inspected (no-LLM)
CONSUMER_PLATFORMS_INSPECTED    = 2          # how many platforms a consumer checks in no-LLM world

# ── Platform internal scoring weights ─────────────────────────────────────────
PLATFORM_SCORE_WEIGHTS = {
    "quality":          0.30,
    "promo_boost":      0.20,
    "neg_total_price":  0.25,
    "neg_delivery_time":0.15,
    "sponsored_boost":  0.10,
}

# ── LLM scoring weights ────────────────────────────────────────────────────────
LLM_SCORE_WEIGHTS = {
    "semantic_match":       0.35,
    "affordability":        0.20,
    "quality":              0.20,
    "neg_delivery_time":    0.15,
    "neg_total_price":      0.10,
    # sponsorship_bias is applied as a direct additive in llm_score(),
    # scaled by SPONSORSHIP_BIAS_STRENGTH in llm_shortlist()
}

# Sponsorship bias multiplier applied ON TOP of base weights when monetised.
# Scale: 0 = neutral, 1.0 = strong.
SPONSORSHIP_BIAS_STRENGTH = 0.30

# ── Consumer utility weights ───────────────────────────────────────────────────
UTILITY_WEIGHTS = {
    "cuisine_match":      2.0,
    "quality":            1.5,
    "neg_total_price":    1.2,
    "neg_delivery_time":  0.8,
    "promo_value":        0.5,
    "llm_trust_bonus":    0.6,
    "platform_loyalty":   0.4,
    "noise_scale":        0.3,
}

# ── Choice model ───────────────────────────────────────────────────────────────
CHOICE_MODEL           = "logit"   # "logit" or "deterministic"
NO_PURCHASE_UTILITY    = 0.0       # outside option
UTILITY_THRESHOLD      = -1.0      # used only in deterministic mode

# ── Intent fulfilment thresholds ───────────────────────────────────────────────
INTENT_PRICE_PENALTY   = 0.5    # per $ over budget
INTENT_TIME_PENALTY    = 0.02   # per minute over tolerance

# ── Attribution module ─────────────────────────────────────────────────────────
RUN_ATTRIBUTION = True
