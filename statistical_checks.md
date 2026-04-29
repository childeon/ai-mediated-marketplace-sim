# Approximate Statistical Checks From Existing Aggregate Results

Important limitation: these tests use scenario-level aggregate conversion counts only. They are unpaired two-proportion z-tests over simulated sessions and do not capture seed-to-seed Monte Carlo variation. Valid tests for intent fulfilment, price, delivery time, platform net, and welfare require per-run or per-session outputs.

| Comparison | Rate 1 | Rate 2 | Diff | 95% CI for Diff | z | p |
|---|---:|---:|---:|---:|---:|---:|
| Exp1 conversion: LLM Neutral vs No-LLM | 81.58% | 80.39% | +1.19 pp | [+0.10, +2.28] pp | 2.14 | 0.032 |
| Exp2 conversion: LLM CPC vs LLM Neutral | 80.21% | 81.58% | -1.37 pp | [-2.46, -0.28] pp | -2.46 | 0.0137 |
| Exp2 conversion: LLM CPA vs LLM Neutral | 80.80% | 81.58% | -0.78 pp | [-1.86, +0.30] pp | -1.41 | 0.158 |
| Exp2 conversion: LLM CPFI vs LLM Neutral | 81.56% | 81.58% | -0.02 pp | [-1.09, +1.05] pp | -0.04 | 0.971 |
| Exp4 conversion: Very Low Trust LLM vs No-LLM baseline | 78.57% | 80.39% | -1.82 pp | [-2.94, -0.70] pp | -3.19 | 0.00144 |
| Exp4 conversion: Low Trust LLM vs No-LLM baseline | 80.24% | 80.39% | -0.15 pp | [-1.25, +0.95] pp | -0.27 | 0.79 |
| Exp4 conversion: Medium Trust LLM vs No-LLM baseline | 81.98% | 80.39% | +1.59 pp | [+0.51, +2.67] pp | 2.88 | 0.00402 |
| Exp4 conversion: High Trust LLM vs No-LLM baseline | 83.71% | 80.39% | +3.32 pp | [+2.26, +4.38] pp | 6.12 | 9.52e-10 |
| Exp4 conversion: Very High Trust LLM vs No-LLM baseline | 85.21% | 80.39% | +4.82 pp | [+3.78, +5.86] pp | 9.03 | 0 |
