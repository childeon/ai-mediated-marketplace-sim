# Robustness Run Summary

Output directory: `robustness_runs/20260429_062845`
Runs: 10

Paired differences are computed by seed. Confidence intervals and p-values use a normal approximation over seed-level differences.

| Comparison | Metric | Mean Diff | 95% CI | z | p |
|---|---|---:|---:|---:|---:|
| LLM Neutral vs No-LLM | consumer.conversion_rate | 0.0119 | [-0.0075, 0.0313] | 1.21 | 0.228 |
| LLM Neutral vs No-LLM | consumer.avg_intent_fulfilment | 0.0639 | [0.0560, 0.0719] | 15.74 | <0.001 |
| LLM Neutral vs No-LLM | consumer.avg_total_price | -1.7206 | [-2.3604, -1.0807] | -5.27 | <0.001 |
| LLM Neutral vs No-LLM | consumer.avg_delivery_time | -1.6468 | [-2.0548, -1.2388] | -7.91 | <0.001 |
| LLM Neutral vs No-LLM | consumer.avg_utility | 0.0071 | [-0.0336, 0.0479] | 0.34 | 0.731 |
| LLM Neutral vs No-LLM | platform.platform_net_revenue | -148.2657 | [-387.3874, 90.8560] | -1.22 | 0.224 |
| LLM Neutral vs No-LLM | restaurant.avg_restaurant_profit | -0.9803 | [-1.2960, -0.6645] | -6.09 | <0.001 |
| LLM Neutral vs No-LLM | llm.total_llm_revenue | 0.0000 | [0.0000, 0.0000] | 0.00 | 1.000 |
| LLM CPC vs LLM Neutral | consumer.conversion_rate | -0.0137 | [-0.0201, -0.0073] | -4.19 | <0.001 |
| LLM CPC vs LLM Neutral | consumer.avg_intent_fulfilment | -0.0301 | [-0.0371, -0.0231] | -8.43 | <0.001 |
| LLM CPC vs LLM Neutral | consumer.avg_total_price | -0.2443 | [-0.8753, 0.3867] | -0.76 | 0.448 |
| LLM CPC vs LLM Neutral | consumer.avg_delivery_time | -0.0303 | [-0.4865, 0.4259] | -0.13 | 0.896 |
| LLM CPC vs LLM Neutral | consumer.avg_utility | -0.0650 | [-0.0826, -0.0474] | -7.24 | <0.001 |
| LLM CPC vs LLM Neutral | platform.platform_net_revenue | 458.3946 | [278.2693, 638.5199] | 4.99 | <0.001 |
| LLM CPC vs LLM Neutral | restaurant.avg_restaurant_profit | -0.9176 | [-1.3032, -0.5321] | -4.66 | <0.001 |
| LLM CPC vs LLM Neutral | llm.total_llm_revenue | 310.1289 | [228.7602, 391.4977] | 7.47 | <0.001 |
| LLM CPA vs LLM Neutral | consumer.conversion_rate | -0.0078 | [-0.0168, 0.0012] | -1.70 | 0.090 |
| LLM CPA vs LLM Neutral | consumer.avg_intent_fulfilment | -0.0206 | [-0.0254, -0.0158] | -8.44 | <0.001 |
| LLM CPA vs LLM Neutral | consumer.avg_total_price | -0.2642 | [-0.8179, 0.2896] | -0.93 | 0.350 |
| LLM CPA vs LLM Neutral | consumer.avg_delivery_time | -0.4928 | [-0.8780, -0.1077] | -2.51 | 0.012 |
| LLM CPA vs LLM Neutral | consumer.avg_utility | -0.0433 | [-0.0599, -0.0268] | -5.14 | <0.001 |
| LLM CPA vs LLM Neutral | platform.platform_net_revenue | 435.5472 | [269.8379, 601.2565] | 5.15 | <0.001 |
| LLM CPA vs LLM Neutral | restaurant.avg_restaurant_profit | -0.8425 | [-1.1568, -0.5283] | -5.26 | <0.001 |
| LLM CPA vs LLM Neutral | llm.total_llm_revenue | 287.2815 | [191.8156, 382.7474] | 5.90 | <0.001 |
| LLM CPFI vs LLM Neutral | consumer.conversion_rate | -0.0002 | [-0.0038, 0.0034] | -0.11 | 0.914 |
| LLM CPFI vs LLM Neutral | consumer.avg_intent_fulfilment | 0.0006 | [-0.0024, 0.0036] | 0.38 | 0.701 |
| LLM CPFI vs LLM Neutral | consumer.avg_total_price | 0.3522 | [-0.1588, 0.8632] | 1.35 | 0.177 |
| LLM CPFI vs LLM Neutral | consumer.avg_delivery_time | -0.6184 | [-1.0136, -0.2231] | -3.07 | 0.002 |
| LLM CPFI vs LLM Neutral | consumer.avg_utility | -0.0117 | [-0.0261, 0.0028] | -1.58 | 0.114 |
| LLM CPFI vs LLM Neutral | platform.platform_net_revenue | 337.2911 | [174.5313, 500.0509] | 4.06 | <0.001 |
| LLM CPFI vs LLM Neutral | restaurant.avg_restaurant_profit | -0.2995 | [-0.5372, -0.0618] | -2.47 | 0.014 |
| LLM CPFI vs LLM Neutral | llm.total_llm_revenue | 199.4153 | [113.3461, 285.4846] | 4.54 | <0.001 |
