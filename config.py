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
# 9 cuisines with 50 restaurants → ~5-6 per cuisine → ~3-4 per platform.
# P(platform carries a given cuisine) ≈ 75%, so ~6% of no-LLM sessions
# check two platforms that both lack the consumer's cuisine — a realistic search miss
# that the LLM eliminates by aggregating all three platforms.
CUISINES = ["Italian", "Chinese", "Indian", "Mexican", "Japanese", "American",
            "Thai", "Korean", "Mediterranean"]

# ── Platform parameters ────────────────────────────────────────────────────────
PLATFORM_PARAMS = [
    {"name": "QuickEats",  "commission": 0.20, "delivery_fee_range": (1.5, 4.0), "subsidy_budget": 5000, "logistics_time_range": (10, 25)},
    {"name": "FoodRush",   "commission": 0.25, "delivery_fee_range": (2.0, 4.5), "subsidy_budget": 8000, "logistics_time_range": (15, 30)},
    {"name": "NomNom",     "commission": 0.15, "delivery_fee_range": (1.0, 3.5), "subsidy_budget": 3000, "logistics_time_range": (20, 35)},
]

# Per-order sponsorship payment FROM platforms TO LLM under each mechanism.
# These nominal rates drive sponsorship bias. Experiment 2 then scales actual
# payments by platform so no sponsor is charged more than its own positive gross
# surplus from the regime.
LLM_SPONSORSHIP_CPC  = {"QuickEats": 0.50, "FoodRush": 0.80, "NomNom": 0.30}  # per click
LLM_SPONSORSHIP_CPA  = {"QuickEats": 0.45, "FoodRush": 0.60, "NomNom": 0.25}  # per order
LLM_SPONSORSHIP_CPFI = {"QuickEats": 0.65, "FoodRush": 0.85, "NomNom": 0.40}  # per fulfilled intent

# Share of each paid regime's positive gross platform surplus captured by the LLM.
# Experiment 2 estimates gross surplus with routing bias on but LLM payments off,
# then scales cash payments to this fraction of platforms' willingness-to-pay.
LLM_SURPLUS_CAPTURE_RATE = 0.50

# ── Restaurant parameters ──────────────────────────────────────────────────────
RESTAURANT_QUALITY_RANGE    = (2.0, 5.0)   # star ratings displayed as 1–5 ★ (half-star precision)
QUALITY_SCALE               = 5.0           # divide by this to normalise quality to [0, 1] internally
RESTAURANT_PRICE_RANGE      = (19.0, 50.0)  # menu price; + delivery fee targets ~$30–35 all-in
RESTAURANT_PREP_TIME_RANGE  = (5, 25)    # minutes (restaurant-side component)
RESTAURANT_COST_RATIO_RANGE = (0.30, 0.60)   # production cost as fraction of menu price
MAX_PLATFORMS_PER_RESTAURANT = 3

# Platform-specific promo spend per restaurant (drawn at setup)
RESTAURANT_PROMO_RANGE = (0.0, 3.0)    # $ per order equivalent

# ── Consumer parameters ────────────────────────────────────────────────────────
CONSUMER_BUDGET_RANGE           = (22.0, 60.0)
CONSUMER_MAX_DELIVERY_RANGE     = (20, 60)   # minutes
CONSUMER_LLM_TRUST_RANGE        = (0.0, 1.0)
CONSUMER_SEARCH_COST            = 0.5        # disutility per additional platform inspected (no-LLM)
CONSUMER_PLATFORMS_INSPECTED    = 2          # how many platforms a consumer checks in no-LLM world

# ── Platform internal scoring weights ─────────────────────────────────────────
PLATFORM_SCORE_WEIGHTS = {
    "quality":          0.25,
    "commission_rev":   0.25,
    "promo_boost":      0.15,
    "neg_total_price":  0.15,
    "neg_delivery_time":0.10,
    "sponsored_boost":  0.10,
}

# ── LLM scoring weights ────────────────────────────────────────────────────────
LLM_SCORE_WEIGHTS = {
    "semantic_match":       0.35,
    "affordability":        0.20,
    "quality":              0.28,  # up from 0.20: find the best-rated option within budget
    "neg_delivery_time":    0.12,
    "neg_total_price":      0.05,  # down from 0.10: don't penalise price beyond affordability check
    # sponsorship_bias is applied as a direct additive in llm_score(),
    # scaled by SPONSORSHIP_BIAS_STRENGTH in llm_shortlist()
}

# Sponsorship bias multiplier applied ON TOP of base weights when monetised.
# Scale: 0 = neutral, 1.0 = strong.
SPONSORSHIP_BIAS_STRENGTH = 0.30

# CPFI does not use special hand-tuned ranking weights. Instead, its sponsored
# bias is multiplied by the offer's predicted intent fulfilment in ranking.py.

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
NO_PURCHASE_UTILITY    = 2.5       # outside option (cooking at home / not ordering)
NO_CLICK_UTILITY        = 1.2       # outside option for ignoring the LLM shortlist before clicking
POST_CLICK_NO_PURCHASE_UTILITY = 0.6  # abandonment option after clicking into an LLM result
UTILITY_THRESHOLD      = -1.0      # used only in deterministic mode

# ── Intent fulfilment thresholds ───────────────────────────────────────────────
INTENT_PRICE_PENALTY   = 0.5    # per $ over budget (as fraction of budget)
INTENT_TIME_PENALTY    = 0.02   # per minute over tolerance
INTENT_QUALITY_WEIGHT  = 0.40   # quality scales fi from 0.60 (2★) to 1.00 (5★)

# ── Attribution module ─────────────────────────────────────────────────────────
RUN_ATTRIBUTION = True
