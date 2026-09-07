# V2 Feature Specification — Market + Macro + News

**Status: RESEARCH ONLY**  
**Principle: PROVE BEFORE TRADE**

V2 adds external information to the V1 market baseline. V2 features are not allowed into the locked V1.12 forward model until they pass independent out-of-sample tests.

## Feature groups

### A. Market structure
1. return_1d
2. return_5d
3. return_20d
4. volatility_10d
5. volatility_20d
6. range_pct
7. volume_change_1d
8. volume_vs_ma20
9. close_sma7_gap
10. close_sma21_gap
11. ema12_ema26_gap
12. rsi_14
13. momentum_10d
14. momentum_20d
15. trend_21_50
16. volatility_ratio

### B. Macro / cross-asset
17. dxy_return_1d
18. dxy_return_5d
19. sp500_return_1d
20. nasdaq_return_1d
21. vix_level
22. vix_change_1d
23. us10y_yield_change_1d
24. gold_return_1d
25. oil_return_1d
26. fed_funds_rate
27. cpi_yoy
28. unemployment_rate
29. financial_conditions_proxy
30. risk_on_score

### C. News / sentiment
31. news_count_24h
32. news_count_7d
33. positive_news_ratio
34. negative_news_ratio
35. neutral_news_ratio
36. news_sentiment_score
37. news_sentiment_change_24h
38. bitcoin_news_share
39. macro_news_share
40. breaking_news_flag
41. negative_news_spike
42. positive_news_spike

## Data provenance

Preferred sources are public/reproducible sources where licensing and availability permit:

- Market/cross-asset: Yahoo Finance via `yfinance`
- Macro: FRED public downloadable series where available
- News discovery: GDELT 2.0 public news data

The implementation must store the source, retrieval timestamp, observation date, and raw identifier where practical. Do not silently substitute a different source when a source fails.

## Anti-leakage rules

1. Every feature must be timestamped by when it was actually available.
2. News published after the prediction timestamp cannot enter that observation.
3. Macro releases must use release/availability time, not merely the economic reference period.
4. No forward outcome may be used to construct a feature.
5. Feature selection must happen on training/validation data only.
6. The final holdout must remain untouched until the research protocol explicitly opens it.

## Research sequence

```text
V1 Market baseline
      ↓
V2A Market + Macro
      ↓
V2B Market + News
      ↓
V2C Market + Macro + News
      ↓
Walk-forward comparison
      ↓
Cost sensitivity
      ↓
Block bootstrap
      ↓
Regime analysis
      ↓
Final untouched holdout
      ↓
Only then consider promotion
```

## Promotion rule

A V2 feature is not promoted because it improves in-sample accuracy. Promotion requires improvement that survives temporal walk-forward testing, cost assumptions, robustness checks, and an untouched holdout. If the external data adds no stable edge, it is rejected.

## Important scope decision

V2 does **not** modify the locked V1.12 forward model. The existing forward model remains frozen while V2 is researched independently.
