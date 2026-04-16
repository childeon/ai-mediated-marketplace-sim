"""
metrics.py — Aggregate simulation records into summary statistics.
"""

from __future__ import annotations
from typing import List, Dict, Any
import numpy as np
import pandas as pd

from simulation import OrderRecord


# ── Concentration metrics ─────────────────────────────────────────────────────

def gini(values: np.ndarray) -> float:
    """Gini coefficient of a non-negative distribution."""
    v = np.sort(np.abs(values))
    n = len(v)
    if n == 0 or v.sum() == 0:
        return 0.0
    idx   = np.arange(1, n + 1)
    return float((2 * (idx * v).sum()) / (n * v.sum()) - (n + 1) / n)


def herfindahl(shares: np.ndarray) -> float:
    """Herfindahl-Hirschman Index (sum of squared market shares)."""
    s = shares / shares.sum() if shares.sum() > 0 else shares
    return float((s ** 2).sum())


# ── Records → DataFrame ───────────────────────────────────────────────────────

def records_to_df(records: List[OrderRecord]) -> pd.DataFrame:
    return pd.DataFrame([r.__dict__ for r in records])


# ── Metric computation ────────────────────────────────────────────────────────

def compute_metrics(records: List[OrderRecord]) -> Dict[str, Any]:
    df  = records_to_df(records)
    out = records_to_df([r for r in records if r.purchased])

    n_total    = len(df)
    n_orders   = len(out)
    conv_rate  = n_orders / n_total if n_total > 0 else 0.0

    # ── Consumer-side ─────────────────────────────────────────────────────────
    consumer = {
        "conversion_rate":          conv_rate,
        "avg_utility":              float(df["consumer_utility"].mean()),
        "avg_intent_fulfilment":    float(out["intent_fulfilment"].mean()) if n_orders else 0.0,
        "avg_total_price":          float(out["total_price"].mean()) if n_orders else 0.0,
        "avg_delivery_time":        float(out["delivery_time"].mean()) if n_orders else 0.0,
        "avg_platforms_checked":    float(df["n_platforms_checked"].mean()),
        "avg_shortlist_relevance":  float(df["shortlist_relevance"].mean()),
    }

    # ── Restaurant-side ───────────────────────────────────────────────────────
    if n_orders > 0:
        rest_orders  = out.groupby("restaurant_id").size()
        rest_profit  = out.groupby("restaurant_id")["restaurant_profit"].sum()
        rest_exp     = df[df["restaurant_id"].notna()].groupby("restaurant_id").size()
        exposure_arr = rest_exp.values.astype(float)
        order_arr    = rest_orders.values.astype(float)
    else:
        exposure_arr = np.zeros(1)
        order_arr    = np.zeros(1)

    restaurant = {
        "total_orders":             int(n_orders),
        "avg_restaurant_profit":    float(out["restaurant_profit"].mean()) if n_orders else 0.0,
        "exposure_gini":            gini(exposure_arr),
        "order_gini":               gini(order_arr),
        "exposure_hhi":             herfindahl(exposure_arr),
    }

    # ── Platform-side ─────────────────────────────────────────────────────────
    plat_orders  = out.groupby("platform_id").size() if n_orders else pd.Series(dtype=int)
    plat_rev     = out.groupby("platform_id")["platform_net"].sum() if n_orders else pd.Series(dtype=float)
    plat_comm    = out.groupby("platform_id")["platform_commission"].sum() if n_orders else pd.Series(dtype=float)
    total_plat_orders = plat_orders.sum() if len(plat_orders) else 0

    platform = {
        "total_orders":             int(total_plat_orders),
        "platform_net_revenue":     float(plat_rev.sum()) if len(plat_rev) else 0.0,
        "platform_commission_rev":  float(plat_comm.sum()) if len(plat_comm) else 0.0,
        "platform_order_shares":    (plat_orders / total_plat_orders).to_dict() if total_plat_orders else {},
        "platform_net_by_id":       plat_rev.to_dict() if len(plat_rev) else {},
    }

    # ── LLM-side ──────────────────────────────────────────────────────────────
    llm = {
        "total_llm_revenue":        float(df["llm_payment"].sum()),
        "avg_llm_revenue_per_order": float(out["llm_payment"].mean()) if n_orders else 0.0,
        "avg_shortlist_relevance":  consumer["avg_shortlist_relevance"],
        "conversion_from_llm":      conv_rate,
    }

    # ── System-level ──────────────────────────────────────────────────────────
    consumer_welfare = float(df["consumer_utility"].sum())
    system = {
        "consumer_welfare":         consumer_welfare,
        "total_surplus":            (consumer_welfare
                                     + restaurant["avg_restaurant_profit"] * n_orders
                                     + platform["platform_net_revenue"]),
    }

    return {
        "consumer":   consumer,
        "restaurant": restaurant,
        "platform":   platform,
        "llm":        llm,
        "system":     system,
        "n_total":    n_total,
        "n_orders":   n_orders,
    }


def print_metrics(label: str, m: Dict[str, Any]):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    c = m["consumer"]
    print(f"\n[Consumer]")
    print(f"  Conversion rate:          {c['conversion_rate']:.3f}")
    print(f"  Avg utility:              {c['avg_utility']:.3f}")
    print(f"  Avg intent fulfilment:    {c['avg_intent_fulfilment']:.3f}")
    print(f"  Avg total price paid:     ${c['avg_total_price']:.2f}")
    print(f"  Avg delivery time:        {c['avg_delivery_time']:.1f} min")
    print(f"  Avg platforms checked:    {c['avg_platforms_checked']:.2f}")
    print(f"  Avg shortlist relevance:  {c['avg_shortlist_relevance']:.3f}")

    r = m["restaurant"]
    print(f"\n[Restaurant]")
    print(f"  Total orders:             {r['total_orders']}")
    print(f"  Avg profit/order:         ${r['avg_restaurant_profit']:.2f}")
    print(f"  Exposure Gini:            {r['exposure_gini']:.3f}")
    print(f"  Order Gini:               {r['order_gini']:.3f}")
    print(f"  Exposure HHI:             {r['exposure_hhi']:.4f}")

    p = m["platform"]
    print(f"\n[Platform]")
    print(f"  Total orders:             {p['total_orders']}")
    print(f"  Platform net revenue:     ${p['platform_net_revenue']:.2f}")
    print(f"  Commission revenue:       ${p['platform_commission_rev']:.2f}")
    shares = p["platform_order_shares"]
    for pid, sh in sorted(shares.items()):
        print(f"    Platform {pid} share:    {sh:.3f}")

    l = m["llm"]
    print(f"\n[LLM]")
    print(f"  Total LLM revenue:        ${l['total_llm_revenue']:.2f}")
    print(f"  Avg LLM rev / order:      ${l['avg_llm_revenue_per_order']:.2f}")

    s = m["system"]
    print(f"\n[System]")
    print(f"  Consumer welfare:         {s['consumer_welfare']:.2f}")
    print(f"  Total surplus:            {s['total_surplus']:.2f}")


def metrics_to_series(m: Dict[str, Any]) -> pd.Series:
    """Flatten metrics dict into a single pandas Series for tabular comparison."""
    flat = {}
    for group, vals in m.items():
        if isinstance(vals, dict):
            for k, v in vals.items():
                if not isinstance(v, dict):
                    flat[f"{group}.{k}"] = v
        else:
            flat[group] = vals
    return pd.Series(flat)
