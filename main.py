"""
main.py — Entry point.

Usage:
    python main.py                   # full run (all experiments + plots)
    python main.py --quick           # 3 runs, 300 consumers, skip attribution
    python main.py --exp 1           # run only experiment 1
    python main.py --no-plots        # experiments only, no figures
"""

import argparse
import sys
import time
import pandas as pd

import config


def parse_args():
    p = argparse.ArgumentParser(description="Food Delivery LLM Simulation")
    p.add_argument("--quick",    action="store_true",
                   help="Small-scale run for fast testing")
    p.add_argument("--exp",      type=int, choices=[1, 2, 3, 4],
                   help="Run a single experiment")
    p.add_argument("--no-plots", action="store_true",
                   help="Skip plot generation")
    p.add_argument("--attribution", action="store_true",
                   help="Run attribution module (slow)")
    p.add_argument("--verbose",  action="store_true",
                   help="Print sample consumer sessions")
    return p.parse_args()


def apply_quick_mode():
    config.N_RUNS      = 3
    config.N_CONSUMERS = 300
    print("[Quick mode] N_RUNS=3, N_CONSUMERS=300")


def print_summary_table(label: str, df: pd.DataFrame):
    key_cols = [c for c in [
        "consumer.conversion_rate",
        "consumer.avg_intent_fulfilment",
        "consumer.avg_total_price",
        "consumer.avg_delivery_time",
        "consumer.avg_shortlist_relevance",
        "restaurant.exposure_gini",
        "restaurant.avg_restaurant_profit",
        "platform.platform_net_revenue",
        "llm.total_llm_revenue",
    ] if c in df.columns]
    print(f"\n{'─'*70}")
    print(f" Summary: {label}")
    print(f"{'─'*70}")
    print(df[key_cols].T.to_string())


def main():
    args = parse_args()

    if args.quick:
        apply_quick_mode()

    # Lazy imports so config overrides apply first
    from experiments import (experiment_1, experiment_2,
                              experiment_3, experiment_4, run_all)
    from plots import make_all_plots
    from attribution import run_attribution

    results = {}
    t0 = time.time()

    if args.exp:
        exp_fn = {1: experiment_1, 2: experiment_2,
                  3: experiment_3, 4: experiment_4}[args.exp]
        df = exp_fn()
        results[f"exp{args.exp}"] = df
        print_summary_table(f"Experiment {args.exp}", df)
    else:
        results = run_all()
        for k, df in results.items():
            print_summary_table(k, df)

    print(f"\nSimulation completed in {time.time() - t0:.1f}s")

    if not args.no_plots and not args.exp:
        make_all_plots(results)

    if args.attribution or (config.RUN_ATTRIBUTION and not args.exp and not args.quick):
        print("\nRunning attribution module...")
        attr_df = run_attribution(n_consumers=30, regime="cpc")
        attr_df.to_csv("attribution_results.csv", index=False)
        print("  Saved attribution_results.csv")

    # Save summary tables
    for k, df in results.items():
        df.to_csv(f"results_{k}.csv")
        print(f"  Saved results_{k}.csv")


if __name__ == "__main__":
    main()
