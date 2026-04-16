"""
plots.py — Visualisation functions for simulation results.
Saves figures to ./figures/ directory.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # non-interactive backend; switch to "TkAgg" if you want live windows
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import config
from simulation import OrderRecord, run_simulation
from metrics import records_to_df

FIGURES_DIR = Path(__file__).parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)


def _save(fig, name: str):
    path = FIGURES_DIR / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ── 1. Conversion rate comparison ─────────────────────────────────────────────

def plot_conversion(exp1_df: pd.DataFrame, exp2_df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Experiment 1
    labels1 = exp1_df.index.tolist()
    vals1   = exp1_df["consumer.conversion_rate"].values
    axes[0].bar(labels1, vals1, color=["steelblue", "darkorange"])
    axes[0].set_title("Exp 1: Conversion Rate\n(No-LLM vs LLM neutral)")
    axes[0].set_ylabel("Conversion rate")
    axes[0].set_ylim(0, 1)
    for i, v in enumerate(vals1):
        axes[0].text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)

    # Experiment 2
    labels2 = exp2_df.index.tolist()
    vals2   = exp2_df["consumer.conversion_rate"].values
    colors  = ["steelblue", "tomato", "forestgreen", "mediumpurple"]
    axes[1].bar(labels2, vals2, color=colors)
    axes[1].set_title("Exp 2: Conversion Rate\nby Monetisation Regime")
    axes[1].set_ylabel("Conversion rate")
    axes[1].set_ylim(0, 1)
    for i, v in enumerate(vals2):
        axes[1].text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)

    fig.tight_layout()
    _save(fig, "1_conversion_rate")


# ── 2. Intent fulfilment ──────────────────────────────────────────────────────

def plot_intent_fulfilment(exp1_df: pd.DataFrame, exp2_df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    for ax, df, title in [
        (axes[0], exp1_df, "Exp 1: Intent Fulfilment\n(No-LLM vs LLM neutral)"),
        (axes[1], exp2_df, "Exp 2: Intent Fulfilment\nby Monetisation Regime"),
    ]:
        labels = df.index.tolist()
        vals   = df["consumer.avg_intent_fulfilment"].values
        bars   = ax.bar(labels, vals)
        ax.set_title(title)
        ax.set_ylabel("Avg intent fulfilment (0–1)")
        ax.set_ylim(0, 1)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.01, f"{v:.3f}",
                    ha="center", fontsize=9)

    fig.tight_layout()
    _save(fig, "2_intent_fulfilment")


# ── 3. Platform profit ─────────────────────────────────────────────────────────

def plot_platform_profit(exp2_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = exp2_df.index.tolist()
    vals   = exp2_df["platform.platform_net_revenue"].values
    bars   = ax.bar(labels, vals, color=["steelblue", "tomato", "forestgreen", "mediumpurple"])
    ax.set_title("Exp 2: Platform Net Revenue by Monetisation Regime")
    ax.set_ylabel("Total net revenue ($)")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(vals) * 0.01, f"${v:.0f}",
                ha="center", fontsize=9)
    fig.tight_layout()
    _save(fig, "3_platform_profit")


# ── 4. Restaurant profit distribution ─────────────────────────────────────────

def plot_restaurant_profit_dist(world: str = "llm", regime: str = "neutral"):
    records = run_simulation(world=world, regime=regime, seed=config.SEED)
    df = records_to_df(records)
    purchased = df[df["purchased"]].copy()

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Per-restaurant total profit
    rest_profit = purchased.groupby("restaurant_id")["restaurant_profit"].sum()
    axes[0].hist(rest_profit.values, bins=20, color="steelblue", edgecolor="white")
    axes[0].set_title(f"Restaurant Total Profit\n({world}, {regime})")
    axes[0].set_xlabel("Total profit ($)")
    axes[0].set_ylabel("Count")

    # Order count distribution
    order_counts = purchased.groupby("restaurant_id").size()
    axes[1].hist(order_counts.values, bins=20, color="darkorange", edgecolor="white")
    axes[1].set_title(f"Order Count per Restaurant\n({world}, {regime})")
    axes[1].set_xlabel("Orders")
    axes[1].set_ylabel("Count")

    fig.tight_layout()
    _save(fig, f"4_restaurant_profit_dist_{world}_{regime}")


# ── 5. Exposure concentration (Gini by scenario) ──────────────────────────────

def plot_exposure_concentration(exp1_df: pd.DataFrame, exp2_df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    for ax, df, title in [
        (axes[0], exp1_df, "Exp 1: Exposure Gini\n(No-LLM vs LLM neutral)"),
        (axes[1], exp2_df, "Exp 2: Exposure Gini\nby Monetisation Regime"),
    ]:
        labels = df.index.tolist()
        vals   = df["restaurant.exposure_gini"].values
        bars   = ax.bar(labels, vals)
        ax.set_title(title)
        ax.set_ylabel("Gini coefficient (0=equal, 1=concentrated)")
        ax.set_ylim(0, 1)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.01, f"{v:.3f}",
                    ha="center", fontsize=9)

    fig.tight_layout()
    _save(fig, "5_exposure_concentration")


# ── 6. Sponsorship bias sweep (Exp 3) ─────────────────────────────────────────

def plot_sponsorship_sweep(exp3_df: pd.DataFrame):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    x = exp3_df["sponsorship_bias_strength"].values

    metrics = [
        ("consumer.avg_shortlist_relevance", "Avg Shortlist Relevance", "steelblue"),
        ("consumer.avg_intent_fulfilment",   "Avg Intent Fulfilment",   "darkorange"),
        ("llm.total_llm_revenue",            "Total LLM Revenue ($)",   "forestgreen"),
    ]

    for ax, (col, ylabel, color) in zip(axes, metrics):
        ax.plot(x, exp3_df[col].values, marker="o", color=color, linewidth=2)
        ax.set_xlabel("Sponsorship Bias Strength")
        ax.set_ylabel(ylabel)
        ax.set_title(f"Exp 3: {ylabel}\nvs Sponsorship Bias")
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    _save(fig, "6_sponsorship_sweep")


# ── 7. Trust sweep (Exp 4) ────────────────────────────────────────────────────

def plot_trust_sweep(exp4_df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    labels = exp4_df.index.tolist()
    x      = range(len(labels))

    axes[0].plot(x, exp4_df["consumer.conversion_rate"].values,
                 marker="o", color="steelblue", label="LLM world")
    axes[0].plot(x, exp4_df["conv_no_llm"].values,
                 marker="s", color="darkorange", linestyle="--", label="No-LLM world")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(labels, rotation=20, ha="right")
    axes[0].set_title("Exp 4: Conversion Rate vs LLM Trust")
    axes[0].set_ylabel("Conversion rate")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(x, exp4_df["restaurant.exposure_hhi"].values,
                 marker="o", color="steelblue", label="LLM world")
    axes[1].plot(x, exp4_df["hhi_no_llm"].values,
                 marker="s", color="darkorange", linestyle="--", label="No-LLM world")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(labels, rotation=20, ha="right")
    axes[1].set_title("Exp 4: Exposure HHI vs LLM Trust")
    axes[1].set_ylabel("HHI (concentration)")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    _save(fig, "7_trust_sweep")


# ── Master plot function ───────────────────────────────────────────────────────

def make_all_plots(results: Dict):
    print("\n--- Generating plots ---")
    exp1 = results["exp1"]
    exp2 = results["exp2"]
    exp3 = results["exp3"]
    exp4 = results["exp4"]

    plot_conversion(exp1, exp2)
    plot_intent_fulfilment(exp1, exp2)
    plot_platform_profit(exp2)
    plot_restaurant_profit_dist("llm", "neutral")
    plot_restaurant_profit_dist("no_llm", "neutral")
    plot_exposure_concentration(exp1, exp2)
    plot_sponsorship_sweep(exp3)
    plot_trust_sweep(exp4)
    print(f"All plots saved to {FIGURES_DIR}/")
