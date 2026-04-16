"""
experiments.py — Define and run the four main experiments.
Each experiment runs N_RUNS Monte Carlo iterations and returns aggregated metrics.
"""

from __future__ import annotations
from typing import Dict, List, Any
import numpy as np
import pandas as pd

import config
from simulation import run_simulation
from metrics import compute_metrics, metrics_to_series, print_metrics


# ── Helper: average metrics over N_RUNS ───────────────────────────────────────

def _avg_runs(world: str, regime: str, n_runs: int = None) -> Dict[str, Any]:
    n_runs = n_runs or config.N_RUNS
    all_records = []
    for i in range(n_runs):
        recs = run_simulation(world=world, regime=regime,
                              seed=config.SEED + i)
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
    """
    print("\n>>> Experiment 2: LLM Monetisation Mechanisms")

    regimes = [
        ("neutral", "LLM Neutral"),
        ("cpc",     "LLM CPC"),
        ("cpa",     "LLM CPA"),
        ("cpfi",    "LLM CPFI"),
    ]

    rows = []
    for regime, label in regimes:
        m = _avg_runs("llm", regime, n_runs)
        print_metrics(label, m)
        s = metrics_to_series(m)
        s["scenario"] = label
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
