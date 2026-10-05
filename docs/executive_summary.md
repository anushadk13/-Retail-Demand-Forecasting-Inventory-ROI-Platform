# Executive summary - Retail demand forecasting & inventory ROI

> All figures come from the **synthetic M5-format sample** shipped with the repo (560 item-store series,
> 1,000 days). Re-run on the real M5 data to get production-grade numbers.

**Question.** How well can we forecast 28-day product demand, where does the forecast fail, and what is better accuracy worth?

**Answer.**
- A LightGBM model reduces WAPE by **27%** versus a seasonal-naive forecast (67.7% vs 93.1%) and by **4%** versus a 28-day moving average, winning in **13 of 13** rolling backtest folds.
- Error is dominated by **count noise at item-store-day level**. The hardest segments are **slow movers** (WAPE 121%, 31% of series, 12% of error) and **HOBBIES** (85%). FOODS has the lowest WAPE (62.5%) but, being the largest category, carries **56% of absolute error**.
- Seasonal-naive **under-forecasts holiday weeks by 12.5%**; the model cuts that to **-2.7%** after adding event-lead features, though holiday WAPE is unchanged.
- Converting accuracy to dollars (95% service level, 7-day lead time, 25% holding cost, 30% margin): **~$530/yr** expected on the 560-series sample (range $354-$701), roughly **$0.95 per series per year**. Gains are modest because forecast-error sigma falls only ~3-5% versus the moving average.

**Recommendation.** Deploy the global model as the planning baseline, route slow movers to an intermittent-demand method (Croston/probabilistic), and prioritise safety-stock policy over further point-forecast tuning, since the remaining error is largely irreducible.

See `README.md` for method and `business_case/inventory_roi_model.xlsx` for the live model.
