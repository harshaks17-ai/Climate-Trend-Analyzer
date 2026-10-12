# GITHUB PLAYBOOK - ship this project like a professional

---

## 1. BEFORE YOU PUSH - checklist

```
[ ] python main.py            -> pipeline finishes, report written
[ ] pytest -q                 -> 36 passed
[ ] streamlit run app/streamlit_app.py -> 7 pages load, no errors
[ ] README.md renders on github.com (preview locally with any md viewer)
[ ] images/ folder has your screenshots
[ ] .gitignore excludes .venv, __pycache__, data/processed
```

---

## 2. CREATE THE REPOSITORY

**repository name:** `Climate-Trend-Analyzer`
**description:** `climate data science pipeline - trends, anomaly detection and
forecasting with an animated 3D streamlit dashboard`
**visibility:** public
**tick:** add a README.md (you already have one - just create an empty repo
without licence, we will push the existing folder)
**do not** tick "add .gitignore" or "choose a license" templates - the local
folder already contains both files.

---

## 3. CONNECT LOCAL FOLDER TO GITHUB

open a terminal inside `Climate-Trend-Analyzer`:

```bash
git init -b main
git add .
git status                      # review - no .venv, no __pycache__
git commit -m "chore: initial project skeleton with pipeline modules"
```

create the empty repo on github first, then:

```bash
git remote add origin https://github.com/<your-username>/Climate-Trend-Analyzer.git
git push -u origin main
```

if github rejects the push (large file), check `git lfs` or shrink the csv -
`data/raw/climate_raw.csv` is ~4 mb which is fine for github.

---

## 4. EIGHT-DAY COMMIT STRATEGY (looks like real work)

| day | what you do | commit message | proof to capture |
| --- | --- | --- | --- |
| 1 | create folder structure, config, requirements, gitignore | `chore: project scaffold + config` | terminal tree screenshot |
| 2 | simulation module + raw csv | `feat: virtual climate dataset generator (seed=42)` | `df.head()` with NaN cells |
| 3 | preprocessing + quality report | `feat: cleaning pipeline + feature engineering` | quality report screenshot |
| 4 | eda module + charts | `feat: eda tables + 7 matplotlib charts` | trend + climatology charts |
| 5 | trend analysis | `feat: ols / theil-sen / mann-kendall trend module` | coefficients table |
| 6 | anomaly detection | `feat: 3-method anomaly fusion with ground-truth metrics` | metrics + timeline chart |
| 7 | forecasting + report | `feat: holt-winters forecast + backtest + auto report` | backtest chart, report md |
| 8 | dashboard + notebook + docs | `feat: streamlit 3d dashboard + notebook + docs` | dashboard recording |

**rules of thumb**

* one commit per logical stage - never one giant commit
* present tense, lowercase, prefix with `feat:` `fix:` `docs:` `test:` `chore:`
* write the body of important commits: what + why + how you verified

example of a good commit body:

```
feat: anomaly detection with ground-truth validation

- z-score on deseasonalised temp, p99 rainfall fence, isolation forest
- fusion: two-method agreement OR persistent 2-day run
- day f1 = 0.64, event recall = 0.85 vs injected events
- adds anomaly_metrics.csv + timeline chart

verified with: pytest tests/test_pipeline.py -q
```

---

## 5. SCREENSHOT / PROOF CHECKLIST

```
[ ] 01_dataset_preview.png        raw csv with missing cells visible
[ ] 02_data_quality.png           duplicates / impossible values removed
[ ] 03_temperature_trend.png      yearly trend chart (eda stage)
[ ] 04_rainfall_trend.png         annual rainfall per region
[ ] 05_seasonal_pattern.png       monthly climatology bar + line
[ ] 06_decadal_comparison.png     decade vs temperature
[ ] 07_anomaly_timeline.png       timeline with flagged extremes
[ ] 08_anomaly_counts.png         events by region and type
[ ] 09_dashboard_3d_surface.png   plotly surface in the browser
[ ] 10_dashboard_animation.png    animated yearly bars mid-play
[ ] 11_forecast.png               observed vs forecast lines
[ ] 12_report_export.png          report & export page of the app
[ ] 13_github_repo.png            repository home after push
[ ] 14_readme_preview.png         rendered readme on github
[ ] dashboard_demo.mp4            20-40 s recording (huge for recruiters)
```

store all of them in `images/` and commit with
`git add images && git commit -m "docs: add screenshots and dashboard demo"`.

---

## 6. REPOSITORY SETTINGS THAT MATTER

**topics** (settings -> general -> topics):

```
climate-analysis  data-science  time-series  anomaly-detection
forecasting  python  pandas  scikit-learn  streamlit  plotly
statsmodels  portfolio-project  environmental-data
```

**about description:**

```
climate data science pipeline - warming trends, extreme-event detection and
5-year forecasting with an animated 3D streamlit dashboard. 36 tests, full docs.
```

**website field:** leave blank unless you deploy the app, then put the
streamlit cloud url here.

**pin the repository** on your profile - pin this one plus your best two.

---

## 7. HOW RECRUITERS SHOULD NAVIGATE YOUR REPO

tell them in this order:

1. read the README (results table + figures at the top)
2. open `outputs/reports/climate_report.md` for findings
3. open the dashboard section and run it locally (5 minutes with the venv steps)
4. open `docs/INTERVIEW_GUIDE.md` if they want the technical depth
5. open `tests/` to see the verification discipline

---

## 8. DEPLOY THE DASHBOARD FOR FREE (optional, big credibility boost)

streamlit community cloud:

1. push the repo to github
2. visit share.streamlit.io -> deploy -> pick the repo
3. main file path: `app/streamlit_app.py`
4. after the first build, the app auto-rebuilds on every push

then put the live url in: repo website field, README badge, LinkedIn post,
and the resume bullet.

---

## 9. LINKEDIN POST TEMPLATE (day 8)

```
i shipped a new project: Climate Trend Analyzer.

what it does:
- cleans 64,000 daily climate records (duplicates, missing cells, sensor errors)
- proves warming trends with OLS + Theil-Sen + Mann-Kendall
- detects heatwaves / cold snaps / floods - and measures its own accuracy
  (event recall 85% against ground truth)
- forecasts 5 years ahead with Holt-Winters, validated on a 24-month hold-out
- presents everything in an animated 3D streamlit dashboard + auto report

stack: python, pandas, scikit-learn, statsmodels, plotly, streamlit, pytest

open source + fully reproducible: [repo link]

#datascience #python #climate #portfolio
```

attach the 30-second dashboard recording - posts with video get far more reach.
