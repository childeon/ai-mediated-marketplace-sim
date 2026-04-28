"""
validate_llm.py — Validate the simulated LLM scoring against a real LLM API.

For each sampled intent, we ask Claude to rank the available offers and compare
its top-5 to the simulation's top-5.  Metrics:
  - top1_match:   does the real LLM's #1 pick match the simulation's #1?
  - top3_overlap: how many of the real LLM's top-3 are in the simulation's top-3?
  - rank_corr:    Spearman rank correlation over all offers

Usage:
    ANTHROPIC_API_KEY=sk-... python3 validate_llm.py --n 20
    python3 validate_llm.py --n 20   # if key is already in environment

Cost estimate: ~20 calls × ~2000 tokens each ≈ 40k tokens ≈ $0.03 on Haiku
Time estimate: ~20-40 seconds with sequential calls
"""

import argparse
import json
import os
import time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import config
from entities import build_platforms, build_restaurants, build_offers, build_consumers
from ranking import llm_shortlist, llm_score, _semantic_match

try:
    import anthropic
except ImportError:
    raise SystemExit("Install the Anthropic SDK:  pip install anthropic")


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_prompt(intent, offers, platforms) -> str:
    plat_map = {p.platform_id: p.name for p in platforms}
    lines = [
        "You are a food delivery assistant. Rank the following offers for a customer.",
        "",
        f"Customer wants: {intent.cuisine} food, budget ${intent.budget:.2f}, "
        f"max delivery time {intent.max_time} minutes.",
        "",
        "Available offers (offer_id | restaurant | platform | cuisine | total_price | "
        "delivery_time_min | stars):",
    ]
    for o in offers:
        lines.append(
            f"  {o.offer_id} | {o.restaurant_name} | {plat_map[o.platform_id]} | "
            f"{o.cuisine} | ${o.total_price:.2f} | {o.delivery_time}min | {o.quality:.1f}★"
        )
    lines += [
        "",
        "Return ONLY a JSON array of the top 5 offer_ids in order from best to worst match.",
        'Example: [42, 17, 3, 88, 51]',
        "No explanation. Just the JSON array.",
    ]
    return "\n".join(lines)


# ── Real LLM call ──────────────────────────────────────────────────────────────

def rank_with_real_llm(client, intent, offers, platforms, model="claude-haiku-4-5-20251001",
                       retries=2) -> list[int]:
    prompt = _build_prompt(intent, offers, platforms)
    for attempt in range(retries + 1):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            ids  = json.loads(text)
            if isinstance(ids, list) and all(isinstance(i, int) for i in ids):
                return ids[:5]
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f"    [warn] LLM call failed after {retries+1} attempts: {e}")
    return []


# ── Agreement metrics ──────────────────────────────────────────────────────────

def agreement_metrics(sim_top5: list, llm_top5: list, all_offers) -> dict:
    if not llm_top5:
        return {"top1_match": None, "top3_overlap": None, "rank_corr": None}

    sim_ids = [o.offer_id for o in sim_top5]
    top1    = int(llm_top5[0] == sim_ids[0]) if llm_top5 and sim_ids else None
    top3_ol = len(set(llm_top5[:3]) & set(sim_ids[:3])) / 3.0

    # Rank correlation over all offers that appear in either ranking
    common = list(set(llm_top5) | set(sim_ids))
    if len(common) < 3:
        rank_corr = None
    else:
        def rank_in(lst, oid):
            return lst.index(oid) + 1 if oid in lst else len(all_offers) + 1
        sim_ranks = [rank_in(sim_ids,   oid) for oid in common]
        llm_ranks = [rank_in(llm_top5,  oid) for oid in common]
        rank_corr = float(spearmanr(sim_ranks, llm_ranks).statistic)

    return {"top1_match": top1, "top3_overlap": top3_ol, "rank_corr": rank_corr}


# ── Main ───────────────────────────────────────────────────────────────────────

def run_validation(n_sessions: int = 20, regime: str = "neutral", seed: int = 42):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "Set ANTHROPIC_API_KEY in your environment:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)

    rng         = np.random.default_rng(seed)
    platforms   = build_platforms(rng)
    restaurants = build_restaurants(platforms, rng)
    offers      = build_offers(restaurants, platforms, rng)
    consumers   = build_consumers(platforms, rng)

    print(f"\nValidating simulated LLM vs real LLM  "
          f"(n={n_sessions}, regime={regime}, model=haiku)")
    print(f"Total offers in market: {len(offers)}\n")

    rows = []
    for i in range(n_sessions):
        c      = consumers[i % len(consumers)]
        intent = c.sample_intent(rng)

        # Simulation top-5
        sim_top5 = llm_shortlist(offers, intent, platforms, regime=regime)

        # Real LLM top-5
        print(f"  [{i+1:>3}/{n_sessions}] intent={intent.cuisine} "
              f"budget=${intent.budget:.0f} time={intent.max_time}min  ...", end="", flush=True)
        llm_top5_ids = rank_with_real_llm(client, intent, offers, platforms)
        print(f" got {llm_top5_ids[:3]}...")

        metrics = agreement_metrics(sim_top5, llm_top5_ids, offers)
        rows.append({
            "session":        i,
            "cuisine":        intent.cuisine,
            "budget":         intent.budget,
            "max_time":       intent.max_time,
            "sim_top1_id":    sim_top5[0].offer_id if sim_top5 else None,
            "llm_top1_id":    llm_top5_ids[0] if llm_top5_ids else None,
            "sim_top1_rest":  sim_top5[0].restaurant_name if sim_top5 else None,
            "llm_call_ok":    bool(llm_top5_ids),
            **metrics,
        })
        time.sleep(0.3)  # be polite to the API

    df = pd.DataFrame(rows)
    df.to_csv("validation_results.csv", index=False)

    valid = df[df["llm_call_ok"]]
    print(f"\n{'='*55}")
    print(f"  Validation Summary  ({len(valid)}/{n_sessions} calls succeeded)")
    print(f"{'='*55}")
    print(f"  Top-1 match rate:   {valid['top1_match'].mean():.1%}")
    print(f"  Top-3 overlap:      {valid['top3_overlap'].mean():.2f} / 1.0")
    if valid["rank_corr"].notna().any():
        print(f"  Rank correlation:   {valid['rank_corr'].mean():.3f}")
    print(f"\n  Saved: validation_results.csv")
    return df


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n",      type=int, default=20, help="Number of sessions")
    p.add_argument("--regime", default="neutral",    help="LLM regime (neutral/cpc/cpa/cpfi)")
    p.add_argument("--seed",   type=int, default=42)
    args = p.parse_args()
    run_validation(n_sessions=args.n, regime=args.regime, seed=args.seed)
