"""
Run per-seed robustness checks without overwriting the main result CSVs.

Outputs are written to a timestamped subdirectory under robustness_runs/.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math
from statistics import NormalDist

import pandas as pd

import config
from metrics import compute_metrics, metrics_to_series
from simulation import run_simulation


def scenario_metrics(seed: int, world: str, regime: str, payment_scale=1.0) -> pd.Series:
    records = run_simulation(
        world=world,
        regime=regime,
        seed=seed,
        payment_scale=payment_scale,
    )
    return metrics_to_series(compute_metrics(records))


def paired_summary(df: pd.DataFrame, baseline: str, scenario: str, metrics: list[str]) -> list[dict]:
    rows = []
    normal = NormalDist()
    for metric in metrics:
        wide = df.pivot(index="run", columns="scenario", values=metric)
        diff = wide[scenario] - wide[baseline]
        n = diff.notna().sum()
        mean = diff.mean()
        sd = diff.std(ddof=1)
        se = sd / math.sqrt(n) if n > 1 else float("nan")
        # Normal critical value is fine for a concise robustness check.
        zcrit = normal.inv_cdf(0.975)
        z = mean / se if se and not math.isnan(se) and se != 0 else (
            0.0 if mean == 0 else float("nan")
        )
        p_value = 2 * (1 - normal.cdf(abs(z))) if not math.isnan(z) else float("nan")
        rows.append({
            "baseline": baseline,
            "scenario": scenario,
            "metric": metric,
            "n_pairs": n,
            "mean_diff": mean,
            "sd_diff": sd,
            "se_diff": se,
            "ci95_low": mean - zcrit * se,
            "ci95_high": mean + zcrit * se,
            "z": z,
            "p_value": p_value,
        })
    return rows


def run_exp1_per_seed(n_runs: int) -> pd.DataFrame:
    rows = []
    scenarios = [
        ("No-LLM", "no_llm", "neutral"),
        ("LLM Neutral", "llm", "neutral"),
    ]
    for run in range(n_runs):
        seed = config.SEED + run
        for label, world, regime in scenarios:
            s = scenario_metrics(seed, world, regime)
            s["run"] = run
            s["seed"] = seed
            s["scenario"] = label
            rows.append(s)
    return pd.DataFrame(rows)


def run_exp2_per_seed(n_runs: int) -> pd.DataFrame:
    rows = []
    for run in range(n_runs):
        seed = config.SEED + run
        m_no_llm = scenario_metrics(seed, "no_llm", "neutral")
        m_neutral = scenario_metrics(seed, "llm", "neutral")
        no_llm_net = m_no_llm["platform.platform_net_revenue"]
        no_llm_by_id = compute_metrics(run_simulation("no_llm", "neutral", seed=seed))["platform"]["platform_net_by_id"]

        for label, regime in [
            ("LLM Neutral", "neutral"),
            ("LLM CPC", "cpc"),
            ("LLM CPA", "cpa"),
            ("LLM CPFI", "cpfi"),
        ]:
            if regime == "neutral":
                s = m_neutral.copy()
                s["gross_platform_surplus_before_llm"] = 0.0
                s["effective_llm_rate"] = 0.0
                s["platform_net_vs_no_llm"] = s["platform.platform_net_revenue"] - no_llm_net
            else:
                # Preserve Experiment 2's WTP calibration at each seed.
                gross_records = run_simulation("llm", regime, seed=seed, payment_scale=0.0)
                m_gross_full = compute_metrics(gross_records)
                gross_net = m_gross_full["platform"]["platform_net_revenue"]
                gross_by_id = m_gross_full["platform"]["platform_net_by_id"]
                gross_surplus = gross_net - no_llm_net
                gross_surplus_by_id = {
                    pid: gross_by_id.get(pid, 0.0) - no_llm_by_id.get(pid, 0.0)
                    for pid in range(config.N_PLATFORMS)
                }
                positive_platform_surplus = sum(max(0.0, v) for v in gross_surplus_by_id.values())
                payable_surplus = min(max(0.0, gross_surplus), positive_platform_surplus)

                nominal_records = run_simulation("llm", regime, seed=seed, payment_scale=1.0)
                m_nominal = compute_metrics(nominal_records)
                nominal_llm_by_id = m_nominal["llm"]["llm_revenue_by_payer_id"]
                target_total_payment = config.LLM_SURPLUS_CAPTURE_RATE * payable_surplus
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

                paid_records = run_simulation("llm", regime, seed=seed, payment_scale=platform_payment_scales)
                m_paid = compute_metrics(paid_records)
                s = metrics_to_series(m_paid)
                s["gross_platform_surplus_before_llm"] = gross_surplus
                s["effective_llm_rate"] = (
                    m_paid["llm"]["total_llm_revenue"] / m_paid["n_orders"]
                    if m_paid["n_orders"] else 0.0
                )
                s["platform_net_vs_no_llm"] = s["platform.platform_net_revenue"] - no_llm_net

            s["run"] = run
            s["seed"] = seed
            s["scenario"] = label
            rows.append(s)
    return pd.DataFrame(rows)


def main() -> None:
    n_runs = config.N_RUNS
    out_dir = Path("robustness_runs") / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    exp1 = run_exp1_per_seed(n_runs)
    exp1.to_csv(out_dir / "exp1_per_run.csv", index=False)

    exp2 = run_exp2_per_seed(n_runs)
    exp2.to_csv(out_dir / "exp2_per_run.csv", index=False)

    key_metrics = [
        "consumer.conversion_rate",
        "consumer.avg_intent_fulfilment",
        "consumer.avg_total_price",
        "consumer.avg_delivery_time",
        "consumer.avg_utility",
        "platform.platform_net_revenue",
        "restaurant.avg_restaurant_profit",
        "llm.total_llm_revenue",
    ]
    summary_rows = []
    summary_rows += paired_summary(exp1, "No-LLM", "LLM Neutral", key_metrics)
    for scenario in ["LLM CPC", "LLM CPA", "LLM CPFI"]:
        summary_rows += paired_summary(exp2, "LLM Neutral", scenario, key_metrics)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out_dir / "paired_tests_summary.csv", index=False)

    md = [
        "# Robustness Run Summary",
        "",
        f"Output directory: `{out_dir}`",
        f"Runs: {n_runs}",
        "",
        "Paired differences are computed by seed. Confidence intervals use a normal approximation over seed-level differences.",
        "",
        "| Comparison | Metric | Mean Diff | 95% CI | z | p |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, r in summary.iterrows():
        comp = f"{r['scenario']} vs {r['baseline']}"
        p = "<0.001" if r["p_value"] < 0.001 else f"{r['p_value']:.3f}"
        md.append(
            f"| {comp} | {r['metric']} | {r['mean_diff']:.4f} | "
            f"[{r['ci95_low']:.4f}, {r['ci95_high']:.4f}] | "
            f"{r['z']:.2f} | {p} |"
        )
    (out_dir / "README.md").write_text("\n".join(md) + "\n")

    print(f"Saved robustness outputs to {out_dir}")


if __name__ == "__main__":
    main()
