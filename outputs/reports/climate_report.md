# Climate Trend Analyzer - Automated Analysis Report

_Generated: 2026-10-12 18:10  |  Record span: 1990 - 2024  |  Rows analysed: 63,920_

---

## 1. Data Quality

| metric | value |
| --- | --- |
| rows in | 64,160 |
| duplicate rows removed | 240 |
| impossible values repaired | 80 |
| missing cells before imputation | 2,151 (0.561 %) |
| missing cells after imputation | 0 |
| rows out | 63,920 |

## 2. Key Findings

1. **Warming is confirmed.** Global mean temperature anomaly moved **+1.03 C** between the first and last 5 years of the record.
2. **Fastest warming region:** Northern Plains at **+0.48 C/decade** (Theil-Sen +0.50, Mann-Kendall: increasing).
3. **Slowest warming region:** Western Ghats at **+0.17 C/decade**.
4. **Rainfall:** 4 of 5 regions show an increasing annual rainfall trend; the rest are flat or drying.
5. **Extreme events:** 1,000 days flagged (537 beyond +2.5 sigma heat). Day-level recall **63%** / precision 65%; event-level recall **85%** / precision 60% across 216 ground-truth events.
6. **Forecast quality:** mean backtest MAE = **0.84 C** (24-month hold-out).
7. **Projection:** on the current linear trend CO2 reaches ~**436 ppm** and mean sea level **+131 mm** by 2034.

## 3. Trend Analysis (temperature)

| region | slope_per_decade | theil_sen_per_decade | r2 | p_value | mk_trend | total_change |
| --- | --- | --- | --- | --- | --- | --- |
| Northern Plains | 0.485 | 0.496 | 0.675 | 1.449e-09 | increasing | 1.37 |
| North India | 0.309 | 0.299 | 0.444 | 1.241e-05 | increasing | 1.24 |
| Coastal India | 0.306 | 0.292 | 0.434 | 1.685e-05 | increasing | 1.25 |
| South India | 0.292 | 0.306 | 0.573 | 1.451e-07 | increasing | 0.87 |
| Western Ghats | 0.169 | 0.171 | 0.217 | 0.004831 | increasing | 0.09 |

## 4. Anomaly Detection Metrics

| true_positive | false_positive | false_negative | true_negative | day_recall | day_precision | day_f1 | accuracy | truth_events | detected_events | matched_events | event_recall | event_precision | total_flagged_days | truth_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 651 | 349 | 376 | 62544 | 0.634 | 0.651 | 0.642 | 0.989 | 216 | 322 | 184 | 0.852 | 0.596 | 1000 | 1027 |

## 5. Anomalies by Region and Type

| region | anomaly_type | count | mean_score | mean_z |
| --- | --- | --- | --- | --- |
| Coastal India | cold_extreme | 77 | 0.337 | -3.31 |
| Coastal India | heat_extreme | 86 | 0.387 | 3.277 |
| Coastal India | multivariate | 15 | 0.333 | 0.084 |
| Coastal India | rain_extreme | 38 | 0.597 | 0.501 |
| North India | cold_extreme | 76 | 0.337 | -3.428 |
| North India | heat_extreme | 90 | 0.359 | 3.336 |
| North India | multivariate | 14 | 0.333 | 0.163 |
| North India | rain_extreme | 32 | 0.573 | -0.032 |
| Northern Plains | cold_extreme | 85 | 0.337 | -3.563 |
| Northern Plains | heat_extreme | 81 | 0.341 | 3.092 |
| Northern Plains | rain_extreme | 32 | 0.51 | -0.029 |
| South India | cold_extreme | 46 | 0.355 | -3.69 |
| South India | heat_extreme | 84 | 0.424 | 3.448 |
| South India | multivariate | 4 | 0.333 | -1.008 |
| South India | rain_extreme | 33 | 0.647 | 0.035 |
| Western Ghats | cold_extreme | 62 | 0.365 | -3.351 |
| Western Ghats | heat_extreme | 93 | 0.408 | 3.745 |
| Western Ghats | multivariate | 12 | 0.333 | -0.762 |
| Western Ghats | rain_extreme | 40 | 0.65 | -0.272 |

## 6. Forecast Backtest Accuracy

| region | variable | mae | rmse | mape | method |
| --- | --- | --- | --- | --- | --- |
| Coastal India | temperature_c | 0.922 | 1.25 | 3.28 | holt_winters |
| North India | temperature_c | 0.765 | 1.047 | 3.3 | holt_winters |
| Northern Plains | temperature_c | 0.739 | 1.04 | 3.73 | holt_winters |
| South India | temperature_c | 0.835 | 0.996 | 3.03 | holt_winters |
| Western Ghats | temperature_c | 0.96 | 1.146 | 4.25 | holt_winters |

## 7. Global Projections (next 10 years)

| year | variable | unit | value | slope_per_decade | r2 |
| --- | --- | --- | --- | --- | --- |
| 2025 | co2_ppm | ppm | 418.94 | 19.08 | 0.9968 |
| 2026 | co2_ppm | ppm | 420.84 | 19.08 | 0.9968 |
| 2027 | co2_ppm | ppm | 422.75 | 19.08 | 0.9968 |
| 2028 | co2_ppm | ppm | 424.66 | 19.08 | 0.9968 |
| 2029 | co2_ppm | ppm | 426.57 | 19.08 | 0.9968 |
| 2030 | co2_ppm | ppm | 428.48 | 19.08 | 0.9968 |
| 2031 | co2_ppm | ppm | 430.38 | 19.08 | 0.9968 |
| 2032 | co2_ppm | ppm | 432.29 | 19.08 | 0.9968 |
| 2033 | co2_ppm | ppm | 434.2 | 19.08 | 0.9968 |
| 2034 | co2_ppm | ppm | 436.11 | 19.08 | 0.9968 |
| 2025 | sea_level_mm | mm | 103.36 | 30.75 | 0.9947 |
| 2026 | sea_level_mm | mm | 106.43 | 30.75 | 0.9947 |
| 2027 | sea_level_mm | mm | 109.51 | 30.75 | 0.9947 |
| 2028 | sea_level_mm | mm | 112.58 | 30.75 | 0.9947 |
| 2029 | sea_level_mm | mm | 115.66 | 30.75 | 0.9947 |
| 2030 | sea_level_mm | mm | 118.73 | 30.75 | 0.9947 |
| 2031 | sea_level_mm | mm | 121.81 | 30.75 | 0.9947 |
| 2032 | sea_level_mm | mm | 124.88 | 30.75 | 0.9947 |
| 2033 | sea_level_mm | mm | 127.96 | 30.75 | 0.9947 |
| 2034 | sea_level_mm | mm | 131.03 | 30.75 | 0.9947 |

## 8. Figures

- `01_yearly_temperature_trend.png`
  
  ![01_yearly_temperature_trend](outputs/figures/01_yearly_temperature_trend.png)
- `02_monthly_climatology.png`
  
  ![02_monthly_climatology](outputs/figures/02_monthly_climatology.png)
- `03_rainfall_trend.png`
  
  ![03_rainfall_trend](outputs/figures/03_rainfall_trend.png)
- `04_correlation_heatmap.png`
  
  ![04_correlation_heatmap](outputs/figures/04_correlation_heatmap.png)
- `05_anomaly_distribution.png`
  
  ![05_anomaly_distribution](outputs/figures/05_anomaly_distribution.png)
- `06_decadal_comparison.png`
  
  ![06_decadal_comparison](outputs/figures/06_decadal_comparison.png)
- `07_distribution_grid.png`
  
  ![07_distribution_grid](outputs/figures/07_distribution_grid.png)
- `08_temperature_anomaly_trend.png`
  
  ![08_temperature_anomaly_trend](outputs/figures/08_temperature_anomaly_trend.png)
- `09_trend_coefficients.png`
  
  ![09_trend_coefficients](outputs/figures/09_trend_coefficients.png)
- `10_rainfall_variability.png`
  
  ![10_rainfall_variability](outputs/figures/10_rainfall_variability.png)
- `11_anomaly_timeline.png`
  
  ![11_anomaly_timeline](outputs/figures/11_anomaly_timeline.png)
- `12_anomaly_scatter.png`
  
  ![12_anomaly_scatter](outputs/figures/12_anomaly_scatter.png)
- `13_anomaly_counts.png`
  
  ![13_anomaly_counts](outputs/figures/13_anomaly_counts.png)
- `14_temperature_forecast.png`
  
  ![14_temperature_forecast](outputs/figures/14_temperature_forecast.png)
- `15_forecast_backtest.png`
  
  ![15_forecast_backtest](outputs/figures/15_forecast_backtest.png)
- `16_global_projections.png`
  
  ![16_global_projections](outputs/figures/16_global_projections.png)

---

_Methodology: OLS + Theil-Sen slopes on annual aggregates, Mann-Kendall monotonic trend test, 1991-2020 WMO baseline climatology, z-score + IQR + IsolationForest anomaly fusion, Holt-Winters monthly forecast with 24-month hold-out backtest._
