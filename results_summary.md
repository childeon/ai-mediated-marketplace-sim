# Simulation Results Summary
## AI-Mediated Food Delivery Marketplace
**Columbia University — Digital Marketplaces, Spring 2026**

---

## Overview

This simulation models a food delivery market with **1,000 consumers, 50 restaurants, and 3 platforms** (QuickEats, FoodRush, NomNom) across **10 Monte Carlo runs per scenario** (10,000 consumer sessions per scenario). It compares two market structures — direct platform search vs. LLM-mediated search — and tests four LLM monetisation regimes.

**The core design distinction:**
- **No-LLM world**: consumers open their 2 highest-loyalty platforms, search for their desired cuisine, and see each platform's revenue-aware algorithmic feed within that cuisine. This mirrors app browsing where loyalty and filters help, but search remains platform-fragmented.
- **LLM world**: consumers query the AI, which interprets their intent (cuisine, budget, time) and returns a cross-platform top-5 shortlist ranked by consumer fit plus any regime-specific sponsorship incentive.

**Primary welfare metric:** Intent Fulfilment (0–1) — did the consumer get the right cuisine, within budget, within their time limit?

---

## Experiment 1: Does the LLM Improve on Direct Search?

*No-LLM world (consumers browse their 2 highest-loyalty cuisine-filtered platforms) vs. LLM Neutral (LLM aggregates all platforms, no paid bias).*

| Metric | No-LLM | LLM Neutral | Change |
|---|---|---|---|
| Intent fulfilment | 0.683 | 0.747 | **+9.3%** |
| Consumer utility | 2.368 | 2.375 | +0.3% |
| Conversion rate | 80.4% | 81.6% | +1.2pp |
| Avg price paid | $34.19 | $32.48 | -$1.71 |
| Avg delivery time | 36.4 min | 34.7 min | -1.7 min |
| Shortlist relevance | — | 0.972 | — |
| LLM click-through rate | — | 93.9% | — |
| Platforms inspected | 2.0 | 1.0 | −50% friction |
| Restaurant profit/order | $11.45 | $10.47 | -8.6% |
| Platform net revenue | $69,366 | $67,884 | -2.1% |
| Restaurant exposure HHI | 0.0202 | 0.0215 | +6.4% |
| Restaurant exposure Gini | 0.059 | 0.148 | +153% |

### Key Finding
The LLM still improves match quality even after giving the no-LLM baseline both platform loyalty and a cuisine filter. Intent fulfilment rises from 0.683 to 0.747 because the LLM aggregates all platforms and balances cuisine, budget, quality, and delivery time rather than forcing consumers to inspect separate app feeds. This creates three effects:

1. **More purchases** (+1.2pp conversion) — consumers find a viable match across platforms more often.
2. **Lower average paid price** (-$1.71) — aggregation lets consumers find better-fit offers without paying more.
3. **Negative neutral platform WTP** — neutral LLM routing improves consumer match quality but lowers platform revenue relative to loyal direct search.

**Platform WTP (willingness-to-pay) for neutral LLM access:** negative in this calibrated version. Paid regimes create platform WTP only when sponsored routing shifts orders toward higher-commission platforms.

---

## Experiment 2: How Does LLM Monetisation Affect Outcomes?

*Four payment regimes in the LLM world: Neutral (free), CPC (per clicked recommendation), CPA (per completed order), CPFI (per fulfilled intent). Paid rates are calibrated regime-by-regime: first measure gross platform surplus with routing bias on but LLM payments off, cap total LLM payment at 50% of aggregate gross surplus, and allocate that payment only to platforms with positive gross gains.*

| Metric | Neutral | CPC | CPA | CPFI |
|---|---|---|---|---|
| Intent fulfilment | 0.747 | 0.716 | 0.726 | **0.747** |
| Shortlist relevance | 0.973 | 0.929 | 0.946 | **0.981** |
| Consumer utility | 2.375 | 2.310 | 2.331 | 2.363 |
| Avg total price | $32.48 | $32.23 | $32.21 | $32.83 |
| Click-through rate | 94.0% | 93.4% | 93.5% | 94.2% |
| LLM revenue | $0 | $3,101 | $2,873 | $1,942 |
| Effective LLM rate/order | $0.00 | $0.39 | $0.36 | $0.24 |
| LLM share of platform surplus | 0% | 50% | 50% | 50% |
| Platform net revenue | $67,884 | $72,468 | $72,239 | $71,309 |
| Platform net vs no-LLM | -$1,483 | +$3,101 | +$2,873 | +$1,942 |
| FoodRush order share | 32.6% | **66.7%** | 60.4% | 46.5% |
| NomNom order share | 26.9% | 3.8% | 3.6% | 12.8% |

### Key Finding
**CPFI best preserves consumer welfare** among paid regimes — intent fulfilment (0.747) and shortlist relevance (0.981) are closest to neutral because the LLM only earns when intent is actually fulfilled, aligning its incentive with the consumer's goal.

**CPC creates the most severe platform concentration**: FoodRush's order share jumps from 33% to 67%, and NomNom is nearly eliminated (3.8%). This is because FoodRush pays the highest CPC rate, so the LLM heavily biases its shortlist toward FoodRush regardless of fit.

**CPC and CPA now differ mechanically.** CPC bills on clicked LLM recommendations, including clicks that do not convert into orders. CPA bills only on completed orders. CPFI also requires completed orders, but scales payment by the fulfilled-intent score.

**All paid regimes keep aggregate platform revenue above the no-LLM baseline because rates are now endogenous.** The model first estimates each regime's gross willingness-to-pay, then scales payment to 50% of aggregate surplus. Importantly, this does not mean every platform wins: lower-commission NomNom loses traffic in paid regimes but is not charged by the LLM. That loss is a competitive externality from rival sponsorship, not a voluntary payment.

**Platform perspective:** CPC generates the highest aggregate platform net revenue ($72,468), with CPA close behind ($72,239). CPFI is the most consumer-aligned paid regime but has the lowest monetization ceiling.

---

## Experiment 3: How Much Sponsorship Bias Is Too Much?

*Sweeping bias strength from 0.0 (pure relevance) to 1.0 (heavily pay-to-play) under CPC regime.*

| Bias Strength | Shortlist Relevance | Intent Fulfilment | LLM Revenue | Platform Net |
|---|---|---|---|---|
| 0.0 (neutral ranking, CPC payments) | 0.973 | 0.747 | $5,113 | $62,770 |
| 0.1 | 0.969 | 0.741 | $5,787 | $66,586 |
| 0.2 | 0.954 | 0.731 | $6,177 | $67,984 |
| 0.3 *(default)* | 0.929 | 0.716 | $6,492 | $69,077 |
| 0.5 | 0.865 | 0.689 | $6,901 | $69,444 |
| 0.7 | 0.816 | 0.663 | $7,174 | $70,195 |
| 1.0 | 0.801 | 0.649 | $7,259 | $70,076 |

*Baseline (no-LLM): intent fulfilment = 0.683*

### Key Finding
There is a clear consumer harm threshold around bias = 0.2. Below this, degradation is modest. Above it, both relevance and intent fulfilment decline meaningfully.

The LLM's revenue gains are sharply diminishing above bias = 0.5: raising bias from 0.3 to 1.0 adds only $768 (+11.8%) in revenue while cutting intent fulfilment by 6.7pp. Intuitively, the LLM is routing so heavily to sponsored platforms that the marginal sponsored order is already captured — additional bias just reshuffles existing traffic.

Even at maximum bias (1.0), intent fulfilment is 0.649, slightly below the no-LLM baseline of 0.683. This is the point where paid placement overwhelms enough consumer-fit signal that LLM mediation becomes worse than loyal direct platform search on match quality.

**Regulatory implication:** a bias cap at 0.1–0.2 would preserve nearly all consumer welfare at minimal LLM revenue cost. This mirrors "disclosure" style regulation — not prohibiting paid placement, but capping its weight.

---

## Experiment 4: Does Consumer Trust in the LLM Shift Market Power?

*Sweeping consumer LLM trust from very low (0.0–0.2) to very high (0.8–1.0), comparing market concentration vs. No-LLM baseline.*

| Trust Band | Conv. Rate (LLM) | Conv. Rate (No-LLM) | HHI — LLM | HHI — No-LLM | Intent Fulfilment |
|---|---|---|---|---|---|
| Very Low (0.0–0.2) | 78.6% | 80.4% | 0.0216 | 0.0202 | 0.748 |
| Low (0.2–0.4) | 80.2% | 80.4% | 0.0216 | 0.0202 | 0.747 |
| Medium (0.4–0.6) | 82.0% | 80.4% | 0.0216 | 0.0202 | 0.747 |
| High (0.6–0.8) | 83.7% | 80.4% | 0.0215 | 0.0202 | 0.748 |
| Very High (0.8–1.0) | 85.2% | 80.4% | 0.0216 | 0.0202 | 0.749 |

### Key Finding
Trust has two distinct effects:

1. **Demand effect (strong):** Higher trust raises conversion by ~6.6pp across the full range (78.6% → 85.2%). Consumers who trust the LLM more follow its recommendation more often, increasing completed purchases.

2. **Quality effect (negligible):** Intent fulfilment is essentially flat across all trust bands (0.747–0.749). Trust does not affect *which* offers the LLM surfaces, only whether the consumer acts on them. This means match quality is determined entirely by the LLM's algorithm, not by adoption rates.

**Concentration effect is small and not necessarily pro-competitive:** LLM restaurant exposure HHI is about 0.0216 versus 0.0202 in the no-LLM baseline. The LLM improves match quality, but it does not automatically make restaurant exposure less concentrated under the repaired loyal-search baseline.

---

## Summary Table

| Metric | No-LLM | LLM Neutral | LLM CPC | LLM CPA | LLM CPFI |
|---|---|---|---|---|---|
| Intent fulfilment | 0.683 | 0.747 | 0.716 | 0.726 | **0.747** |
| Consumer utility | 2.368 | **2.375** | 2.310 | 2.331 | 2.363 |
| Avg total price | $34.19 | $32.48 | $32.23 | $32.21 | $32.83 |
| Platform net revenue | $69,366 | $67,884 | **$72,468** | $72,239 | $71,309 |
| LLM revenue | — | $0 | $3,101 | $2,873 | $1,942 |
| Click-through rate | — | 94.0% | 93.4% | 93.5% | 94.2% |
| FoodRush share | 33.0% | 32.6% | **66.7%** | 60.4% | 46.5% |
| Restaurant HHI | 0.0202 | 0.0215 | 0.0215 | 0.0214 | 0.0213 |

---

## Design Parameters

| Parameter | Value |
|---|---|
| Consumers per run | 1,000 |
| Monte Carlo runs | 10 per scenario |
| Restaurants | 50 (listed on 1–3 platforms) |
| Platforms | 3 — QuickEats (20% commission), FoodRush (25%), NomNom (15%) |
| Menu price range | $19.00–50.00 |
| Consumer budget range | $22.00–60.00 |
| Delivery fee range | QuickEats $1.50–4.00; FoodRush $2.00–4.50; NomNom $1.00–3.50 |
| Platform logistics | QuickEats 10–25 min, FoodRush 15–30 min, NomNom 20–35 min |
| Cuisines | 9 — Italian, Chinese, Indian, Mexican, Japanese, American, Thai, Korean, Mediterranean |
| Restaurant ratings | 2.0–5.0 stars (half-star precision) |
| LLM shortlist size | K = 5 |
| Choice model | Multinomial logit with LLM click stage and post-click purchase stage |
| Default sponsorship bias | 0.30 (Exp 3 sweeps 0.0–1.0) |
| Neutral platform WTP for LLM | Negative vs loyal no-LLM search |
| LLM share of platform surplus | 50% of aggregate gross platform WTP, allocated only to positive-gain sponsors |
