"""
experiments.py — Define and run the four main experiments.
Each experiment runs N_RUNS Monte Carlo iterations and returns aggregated metrics.
"""

from __future__ import annotations
from typing import Dict, List, Any, Union
import numpy as np
import pandas as pd

import config
from simulation import run_simulation
from metrics import compute_metrics, metrics_to_series, print_metrics


# ── Helper: average metrics over N_RUNS ───────────────────────────────────────

def _avg_runs(world: str, regime: str, n_runs: int = None,
              payment_scale: Union[float, Dict] = 1.0) -> Dict[str, Any]:
    n_runs = n_runs or config.N_RUNS
    all_records = []
    for i in range(n_runs):
        recs = run_simulation(world=world, regime=regime,
                              seed=config.SEED + i,
                              payment_scale=payment_scale)
        all_records.extend(recs)
    return compute_metrics(all_records)


# ── Experiment 1: No-LLM vs LLM (neutral) ────────────────────────────────────

def experiment_1(n_runs: int = None) -> pd.DataFrame:
    """
    Compare no-LLM vs LLM world under neutral ranking.
    Question: does the LLM improve intent fulfilment and lower search friction?
    """
    print("\n>>> Experiment 1: No-LLM vs LLM (neutral ranking)")

    scenarios = [
        ("no_llm",  "neutral", "No-LLM"),
        ("llm",     "neutral", "LLM Neutral"),
    ]

    rows = []
    for world, regime, label in scenarios:
        m = _avg_runs(world, regime, n_runs)
        print_metrics(label, m)
        s = metrics_to_series(m)
        s["scenario"] = label
        rows.append(s)

    df = pd.DataFrame(rows).set_index("scenario")
    return df


# ── Experiment 2: Monetisation mechanisms ─────────────────────────────────────

def experiment_2(n_runs: int = None) -> pd.DataFrame:
    """
    Compare neutral / CPC / CPA / CPFI mechanisms in the LLM world.
    Question: how do different payment rules affect relevance, revenue, concentration?

    Rates are calibrated to an aggregate sponsor-side WTP ceiling regime-by-regime:
    first measure gross platform surplus with routing bias on but LLM payments off,
    then let the LLM capture a fixed share of any positive surplus.
    The surplus-share metric is the platform/LLM bargaining split: it shows how
    much of the incremental platform value is paid to the LLM. This is not a
    guarantee that every platform benefits; low-sponsorship rivals can still
    lose traffic as a competitive externality.
    """
    print("\n>>> Experiment 2: LLM Monetisation Mechanisms")

    # Compute the outside option and neutral comparison.
    m_no_llm  = _avg_runs("no_llm",  "neutral", n_runs)
    m_neutral = _avg_runs("llm",     "neutral", n_runs)

    no_llm_net      = m_no_llm["platform"]["platform_net_revenue"]
    no_llm_by_id    = m_no_llm["platform"]["platform_net_by_id"]
    neutral_net     = m_neutral["platform"]["platform_net_revenue"]
    neutral_orders  = m_neutral["n_orders"]
    neutral_wtp     = (neutral_net - no_llm_net) / neutral_orders if neutral_orders else 0.0
    capture_rate    = config.LLM_SURPLUS_CAPTURE_RATE

    print(f"\n  [Platform WTP calibration]")
    print(f"  No-LLM platform net:      ${no_llm_net:,.0f}")
    print(f"  LLM Neutral platform net: ${neutral_net:,.0f}  (+${neutral_net - no_llm_net:,.0f} surplus)")
    print(f"  Neutral WTP ceiling:      ${neutral_wtp:.3f}/order")
    print(f"  LLM surplus share:        {capture_rate:.0%} of each regime's positive gross platform surplus.")

    regimes = [
        ("neutral", "LLM Neutral"),
        ("cpc",     "LLM CPC"),
        ("cpa",     "LLM CPA"),
        ("cpfi",    "LLM CPFI"),
    ]

    rows = []
    for regime, label in regimes:
        payment_scale = 1.0
        gross_surplus = 0.0
        positive_platform_surplus = 0.0
        regime_wtp_per_order = 0.0
        platform_payment_scales = 1.0
        platform_net_vs_no_llm_by_id = {}

        if regime == "neutral":
            m = m_neutral
        else:
            # Bias remains active, but payments are set to zero. This measures
            # the platform value created by each regime's routing pattern.
            m_gross = _avg_runs("llm", regime, n_runs, payment_scale=0.0)
            gross_net = m_gross["platform"]["platform_net_revenue"]
            gross_by_id = m_gross["platform"]["platform_net_by_id"]
            gross_orders = m_gross["n_orders"]
            gross_surplus = gross_net - no_llm_net
            gross_surplus_by_id = {
                pid: gross_by_id.get(pid, 0.0) - no_llm_by_id.get(pid, 0.0)
                for pid in range(config.N_PLATFORMS)
            }
            positive_platform_surplus = sum(
                max(0.0, v) for v in gross_surplus_by_id.values()
            )
            payable_surplus = min(
                max(0.0, gross_surplus),
                positive_platform_surplus,
            )
            regime_wtp_per_order = payable_surplus / gross_orders if gross_orders else 0.0

            # Run once at the nominal config rate to learn the unscaled transfer.
            # Because payment_scale does not affect routing, per-platform LLM
            # revenue is linear in the scale factor and can be calibrated directly.
            m_nominal = _avg_runs("llm", regime, n_runs, payment_scale=1.0)
            nominal_llm_by_id = m_nominal["llm"]["llm_revenue_by_payer_id"]
            target_total_payment = capture_rate * payable_surplus
            platform_payment_scales = {}
            for pid in range(config.N_PLATFORMS):
                nominal_payment = nominal_llm_by_id.get(pid, nominal_llm_by_id.get(float(pid), 0.0))
                target_payment = (
                    target_total_payment
                    * max(0.0, gross_surplus_by_id[pid])
                    / positive_platform_surplus
                    if positive_platform_surplus > 0 else 0.0
                )
                platform_payment_scales[pid] = (
                    target_payment / nominal_payment if nominal_payment > 0 else 0.0
                )
            m = _avg_runs("llm", regime, n_runs, payment_scale=platform_payment_scales)

        print_metrics(label, m)

        plat_net      = m["platform"]["platform_net_revenue"]
        n_orders      = m["n_orders"]
        llm_rev       = m["llm"]["total_llm_revenue"]
        eff_rate      = llm_rev / n_orders if n_orders else 0.0
        net_vs_no_llm = plat_net - no_llm_net
        wtp_display   = regime_wtp_per_order if regime != "neutral" else neutral_wtp
        llm_share_of_platform_surplus = (
            llm_rev / gross_surplus
            if regime != "neutral" and gross_surplus > 0 else 0.0
        )
        platform_net_vs_no_llm_by_id = {
            pid: m["platform"]["platform_net_by_id"].get(pid, 0.0) - no_llm_by_id.get(pid, 0.0)
            for pid in range(config.N_PLATFORMS)
        }
        all_platforms_nonnegative = all(v >= -1e-9 for v in platform_net_vs_no_llm_by_id.values())

        print(f"  [Platform economics vs no-LLM]")
        if regime != "neutral":
            print(f"  Aggregate gross surplus:  ${gross_surplus:+,.0f}")
            print(f"  Positive sponsor surplus: ${positive_platform_surplus:+,.0f}")
            print(f"  WTP ceiling:              ${regime_wtp_per_order:.3f}/order")
            print(f"  Payment scales by plat:   {platform_payment_scales}")
        print(f"  Effective LLM rate:       ${eff_rate:.3f}/order")
        print(f"  LLM share of surplus:     {llm_share_of_platform_surplus*100:.0f}%")
        print(f"  Platform net vs no-LLM:   ${net_vs_no_llm:+,.0f}  "
              f"({'surplus — platforms prefer LLM' if net_vs_no_llm >= 0 else 'DEFICIT — platforms prefer no-LLM'})")
        print(f"  Per-platform net vs no-LLM: {platform_net_vs_no_llm_by_id}")

        s = metrics_to_series(m)
        s["scenario"]           = label
        s["platform_wtp"]       = wtp_display
        s["gross_platform_surplus_before_llm"] = gross_surplus
        s["positive_platform_surplus_before_llm"] = positive_platform_surplus
        s["payment_scale"]      = platform_payment_scales
        s["effective_llm_rate"] = eff_rate
        s["llm_share_of_platform_surplus"] = llm_share_of_platform_surplus
        s["platform_net_vs_no_llm"] = net_vs_no_llm
        s["platform_net_vs_no_llm_by_id"] = platform_net_vs_no_llm_by_id
        s["all_platforms_nonnegative_vs_no_llm"] = all_platforms_nonnegative
        rows.append(s)

    df = pd.DataFrame(rows).set_index("scenario")
    return df


# ── Experiment 3: Sponsorship strength sweep ──────────────────────────────────

def experiment_3(n_runs: int = None) -> pd.DataFrame:
    """
    Vary sponsorship bias strength (0 → 1) in CPC regime.
    Question: how much paid bias degrades consumer relevance?
    """
    print("\n>>> Experiment 3: Sponsorship Strength Sweep (CPC regime)")

    strengths = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    rows = []
    original_bs = config.SPONSORSHIP_BIAS_STRENGTH

    for bs in strengths:
        config.SPONSORSHIP_BIAS_STRENGTH = bs
        m = _avg_runs("llm", "cpc", n_runs)
        s = metrics_to_series(m)
        s["sponsorship_bias_strength"] = bs
        rows.append(s)
        print(f"  bias={bs:.1f}  relevance={m['consumer']['avg_shortlist_relevance']:.3f}"
              f"  fi={m['consumer']['avg_intent_fulfilment']:.3f}"
              f"  llm_rev=${m['llm']['total_llm_revenue']:.2f}")

    config.SPONSORSHIP_BIAS_STRENGTH = original_bs  # restore
    df = pd.DataFrame(rows)
    return df


# ── Experiment 4: Consumer LLM trust sweep ────────────────────────────────────

def experiment_4(n_runs: int = None) -> pd.DataFrame:
    """
    Vary consumer LLM trust range (low → high).
    Question: when does the LLM meaningfully shift market power away from platforms?
    """
    print("\n>>> Experiment 4: Consumer LLM Trust Sweep")

    trust_ranges = [
        ((0.0, 0.2), "Very Low Trust"),
        ((0.2, 0.4), "Low Trust"),
        ((0.4, 0.6), "Medium Trust"),
        ((0.6, 0.8), "High Trust"),
        ((0.8, 1.0), "Very High Trust"),
    ]

    rows = []
    original_trust = config.CONSUMER_LLM_TRUST_RANGE

    for trust_range, label in trust_ranges:
        config.CONSUMER_LLM_TRUST_RANGE = trust_range
        m_llm    = _avg_runs("llm",    "neutral", n_runs)
        m_nollm  = _avg_runs("no_llm", "neutral", n_runs)

        # Market power shift = difference in platform order concentration
        llm_hhi   = m_llm["restaurant"]["exposure_hhi"]
        nollm_hhi = m_nollm["restaurant"]["exposure_hhi"]

        print(f"  trust={trust_range}  HHI(llm)={llm_hhi:.4f}"
              f"  HHI(no_llm)={nollm_hhi:.4f}"
              f"  conv(llm)={m_llm['consumer']['conversion_rate']:.3f}"
              f"  conv(no_llm)={m_nollm['consumer']['conversion_rate']:.3f}")

        s = metrics_to_series(m_llm)
        s["trust_range"] = str(trust_range)
        s["label"]       = label
        s["hhi_no_llm"]  = nollm_hhi
        s["conv_no_llm"] = m_nollm["consumer"]["conversion_rate"]
        rows.append(s)

    config.CONSUMER_LLM_TRUST_RANGE = original_trust  # restore
    df = pd.DataFrame(rows).set_index("label")
    return df


# ── Run all experiments ────────────────────────────────────────────────────────

def run_all(n_runs: int = None) -> Dict[str, pd.DataFrame]:
    results = {}
    results["exp1"] = experiment_1(n_runs)
    results["exp2"] = experiment_2(n_runs)
    results["exp3"] = experiment_3(n_runs)
    results["exp4"] = experiment_4(n_runs)
    return results
