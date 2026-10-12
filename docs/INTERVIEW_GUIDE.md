# INTERVIEW GUIDE - CLIMATE TREND ANALYZER

how to sell this project to HR, technical interviewers and recruiters.

---

## 1. RESUME BULLET POINTS (copy-paste)

1. built an end-to-end python climate analytics pipeline (pandas, scikit-learn,
   statsmodels) that cleans 64k daily records, detects extremes with an
   explainable 3-method fusion (z-score + percentile + IsolationForest) and
   quantifies quality with day-level F1 = 0.64 and event-level recall = 85 %
   against simulation ground truth.

2. applied climate statistics used by real agencies - 1991-2020 baseline
   normals, temperature anomalies, Theil-Sen robust slopes and the
   Mann-Kendall trend test - to prove significant warming in 4 of 5 regions
   (+0.17 to +0.48 C/decade).

3. shipped a 5-year Holt-Winters temperature forecast validated with a 24-month
   hold-out backtest (MAE 0.74-0.96 C, MAPE 3-4 %) and a Streamlit dashboard
   with animated 3D plotly surfaces, CSV exports and an automated markdown
   report; full pytest suite (36 tests) + one-command CLI pipeline.

---

## 2. LINKEDIN PROJECT DESCRIPTIONS (pick one)

**version A - technical**

> I built a Climate Trend Analyzer from scratch: a reproducible python
> pipeline that turns messy daily climate records into statistical evidence.
> It computes 1991-2020 baseline normals, proves warming trends with OLS +
> Theil-Sen + Mann-Kendall, detects heatwaves / cold snaps / floods with an
> explainable 3-method anomaly fusion (validated against ground truth:
> event recall 85 %), and forecasts the next 5 years with Holt-Winters
> (backtested, MAE < 1 C). The whole story is told through an animated 3D
> Streamlit dashboard. python - pandas - scikit-learn - statsmodels - plotly.

**version B - impact first**

> extreme weather is the costliest climate signal. I built a tool that finds
> those events in data: 64,000 simulated-but-physical climate records,
> automated cleaning, anomaly detection with measured precision/recall, trend
> statistics a research team would recognise, and 5-year forecasts - all in
> one click via a dark 3D dashboard. portfolio project, fully reproducible.

**version C - short / story**

> problem: climate data is messy and trend claims are easy to fake.
> solution: an auditable pipeline - fixed-seed simulation, cleaning log,
> statistical tests, hold-out backtesting, pytest suite.
> result: you can trust every number in the report. that is the difference
> between a chart and an analysis.

---

## 3. TEN INTERVIEW QUESTIONS + STRONG ANSWERS

**Q1. what does your project actually do?**
it takes daily climate records for five regions over 35 years, cleans them,
measures long-term trends, detects extreme events, forecasts the next five
years and presents everything in an interactive dashboard plus an automated
report. every stage writes csv outputs so the analysis is auditable.

**Q2. why did you simulate data instead of using real data?**
real institutional feeds (IMD, NOAA) are rate-limited or require credentials,
and students cannot guarantee reproducibility for a recruiter. i built a
physics-informed simulator - seasonality, warming trend, monsoon shape,
autocorrelated weather noise, rising co2 and sea level - with a fixed seed,
plus injected extreme events and sensor errors. that lets me measure detection
accuracy against ground truth, which raw public data never gives you. the
cleaning and analysis modules are dataset-agnostic, so real csv files drop
straight in.

**Q3. what is a climate baseline / normal and why 1991-2020?**
the wmo defines a 30-year reference period to separate "weather" from
"climate". every day's temperature is compared to the average of that calendar
month over 1991-2020, giving an anomaly. anomalies make different regions and
seasons comparable, because absolute temperatures differ but anomalies do not.

**Q4. how do you detect anomalies?**
three independent methods: (1) z-score of the deseasonalised temperature
anomaly - flags statistically unusual heat or cold; (2) rainfall above the
99th percentile of that region-month - rainfall is skewed, so percentiles beat
z-scores; (3) isolation forest, an unsupervised model on 5 features. i fuse
them with an explainable rule - keep a day if two methods agree, or if it sits
inside a persistent two-day run. single noisy spikes are dropped. i validate
against injected ground truth: day-level f1 0.64, event-level recall 0.85.

**Q5. why not just use isolation forest alone?**
unsupervised models flag statistical outliers, not necessarily *events*. a
single sensor spike and a five-day heatwave can both be outliers, but only one
matters operationally. the persistence rule plus the percentile rule encode
domain knowledge, and the z-score gives an interpretable threshold.

**Q6. how do you know your trend is real and not noise?**
three checks: ols slope with a p-value and r-squared, the theil-sen slope
which is robust to outliers, and the mann-kendall test which needs no
normality assumption. all three agree for the warming signal, and i report
them side by side instead of cherry-picking.

**Q7. how do you evaluate a forecast honestly?**
hold-out backtesting. i train on all months except the last 24, predict those
24, then compute mae / rmse / mape. the temperature model achieves mae between
0.74 and 0.96 c (mape 3-4 %). i never quote in-sample fit numbers.

**Q8. what is the difference between holt-winters and a linear trend forecast?**
holt-winters captures three components: the level, the trend and the annual
seasonality, with exponential smoothing weights that adapt over time. a linear
trend with fourier seasonality is the transparent baseline. i implement both
plus sarimax, and fall back to the linear model automatically if the others
fail - production thinking.

**Q9. what would you change with real data and more time?**
three things: (1) replace the simulator with open feeds - open-meteo api or
era5 reanalysis; (2) add a supervised model (xgboost on lag + rolling
features) to predict extremes 24-48 hours ahead; (3) deploy on streamlit cloud
with github actions running the pipeline weekly so the dashboard never goes
stale.

**Q14 wait - ten questions?** here are the last two:

**Q10. how do you keep the project reproducible?**
fixed random seed, a single config module for every path and constant, csv
artefacts for every stage, a one-command cli (`python main.py`) and 36 pytest
tests including dashboard smoke tests via streamlit's app testing framework.

**Q11. walk me through the biggest bug you hit and how you fixed it.**
the persistence check in the anomaly detector originally kept isolated
false-positive days instead of dropping them, which tanked precision. i wrote
a tuning harness that measured day-level and event-level precision/recall for
six candidate fusion rules against the injected ground truth, and adopted the
rule that maximised f1 - persistence OR two-method agreement - instead of
guessing. tuning against a measured metric, not vibes.

---

## 4. EXPLAINING IT TO HR (30 seconds, non-technical)

> "i built a tool that studies climate records automatically. it finds whether
> a region is getting warmer over decades, spots extreme events like heatwaves
> and floods, and estimates what the next five years look like. it also checks
> its own work with tests, so the numbers are trustworthy. the result is a
> dashboard anyone can open and explore."

## 5. EXPLAINING IT TO A TECHNICAL INTERVIEWER (90 seconds)

> "the pipeline has seven stages. a seeded simulator produces 64k daily rows
> with seasonality, warming trends and 229 injected extreme events, plus sensor
> errors like duplicates, missing cells and impossible values. cleaning repairs
> all of that and engineers calendar features, 1991-2020 baseline normals,
> anomalies and rolling means. analysis splits into four modules: eda tables
> and charts; trend statistics - ols, theil-sen, mann-kendall; anomaly
> detection fusing z-score, regional rainfall percentiles and isolation forest
> with a persistence rule; and forecasting with holt-winters validated by a
> 24-month hold-out. everything is tested with pytest, orchestrated by a cli,
> and presented in a streamlit dashboard with plotly 3d surfaces and an
> auto-generated markdown report."

## 6. THE REAL-WORLD VALUE (say this with confidence)

* cities use exactly this analysis to design heat action plans - if your
  detector flags heatwaves with 85 % event recall you can trigger warnings
  before hospital admissions spike.
* insurers and utilities price risk from trend and anomaly statistics.
* agriculture needs monsoon-shift and heat-stress numbers for sowing dates.
* every number in this project is traceable to a csv and a statistical test -
  that auditability is what makes analysis trustworthy in policy decisions.

---

## 7. LIKELY FOLLOW-UP QUESTIONS

| question | one-line answer to prepare |
| --- | --- |
| why theil-sen instead of just ols? | median of pairwise slopes, robust to outliers |
| what does mann-kendall test? | monotonic trend, no normality assumption |
| why percentile instead of z-score for rain? | rainfall is right-skewed and zero-inflated |
| what is isolation forest? | recursive random splits isolate outliers fast |
| what is contamination in isolation forest? | the expected fraction of outliers |
| how does holt-winters handle seasonality? | additive seasonal component with 12-period cycle |
| what is a backtest? | train past, predict held-out future, score honestly |
| how would you productionise? | schedule + api ingestion + alerting + cloud deploy |
| what is copy-on-write in pandas 3? | safer assignments, chained indexing no longer mutates |
| how do you cache the streamlit app? | st.cache_data on csv loads + subprocess for rebuilds |
