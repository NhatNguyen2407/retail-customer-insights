# Retail Customer Insights

I built this project to practise working with transactional data from start to finish: cleaning raw records, checking data quality, answering business questions with SQL, and exploring customer behaviour through RFM segmentation.

The dashboard uses historical data from a UK online retailer. It is a portfolio case study, not a live business report.

**Live dashboard:** https://retail-customer-insights.streamlit.app/

**Tools:** Python, pandas, SQLite, Plotly, Streamlit, pytest

## Questions I wanted to explore

- How did sales revenue and order volume change over time?
- Which products and markets contributed the most revenue?
- Which customers purchased frequently, and which were less active near the end of the observed period?
- How much data needed to be excluded or treated differently before analysis?

## Data

I used the [UCI Online Retail dataset](https://archive.ics.uci.edu/dataset/352/online+retail), which contains 541,909 transaction lines recorded between December 2010 and December 2011.

- Creator: Daqing Chen
- Publisher: UCI Machine Learning Repository (2015)
- DOI: [10.24432/C5BW33](https://doi.org/10.24432/C5BW33)
- License: CC BY 4.0

The raw workbook is not stored in this repository. The application downloads it on first use, or I can provide the workbook through the sidebar when running it locally.

## Run locally

Use Python 3.10 or later.

```bash
python -m venv .venv
```

Activate the environment with `.venv\Scripts\activate` on Windows or `source .venv/bin/activate` on macOS/Linux. Then run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

If the dataset download fails, download `Online Retail.xlsx` from the UCI page and save it as `data/Online Retail.xlsx`. The dashboard also accepts the workbook through the sidebar.

To prepare a local SQLite database for the queries in `sql/business_questions.sql`:

```bash
python scripts/prepare_data.py
```

To run the automated tests:

```bash
python -m pytest -q
```

## Project structure

```text
app.py                       Streamlit dashboard
src/data.py                  Data loading, cleaning and quality checks
src/analytics.py             Revenue metrics and RFM segmentation
scripts/prepare_data.py      Export cleaned transactions to SQLite
sql/business_questions.sql   SQL queries for the main business questions
tests/test_analytics.py      Unit tests using a small synthetic dataset
.github/workflows/tests.yml  GitHub Actions test workflow
```

## How I handled the data

- I excluded cancelled invoices (those starting with `C`), non-positive quantities or prices, missing invoice numbers, and invalid dates.
- Revenue means `Quantity × UnitPrice` for the remaining positive sales. It does **not** represent profit or net revenue after returns.
- I counted unique invoice numbers as orders. One invoice can contain multiple product lines.
- I kept sales without a customer ID in the revenue metrics, but excluded them from customer-level analysis.
- For RFM, I measured recency relative to the day after the last recorded purchase in the selected data, not today's date.
- I assigned relative scores from 1 to 5 for recency, frequency, and monetary value. The segment labels follow simple rules rather than a trained machine-learning model.
- Country and date filters affect the metrics, charts, and RFM scores.

| Segment | Rule |
| --- | --- |
| Champions | R >= 4, F >= 4, M >= 4 |
| Loyal | R >= 3, F >= 4 |
| At risk | R <= 2, F >= 3 |
| New / promising | R >= 4, F <= 2 |
| Other | All remaining customers |

Rules are applied in this order, so a customer who qualifies for Champions is not also labelled Loyal. Higher RFM scores always indicate a better relative ranking.

## What the results can help investigate

- Revenue concentration across products and countries
- Repeat purchasing patterns among customers with known IDs
- Groups worth examining for possible loyalty or reactivation initiatives

These are possible business questions, not evidence that a campaign would improve retention or sales.

## Limitations

- The data comes from 2010–2011 and should not be used to describe today's retail market.
- The first and last months do not necessarily cover complete calendar months.
- Missing customer IDs limit customer segmentation.
- Refund adjustments, fulfilment costs, and marketing acquisition data are not available for a full profitability analysis.
- An “At risk” segment describes lower recent activity within this historical sample; it is not a verified churn prediction.

## Deployment

I deployed the dashboard on [Streamlit Community Cloud](https://streamlit.io/cloud). It is publicly available at [retail-customer-insights.streamlit.app](https://retail-customer-insights.streamlit.app/). The application uses `app.py` and `requirements.txt`.

I confirmed that the public deployment loaded the UCI dataset and displayed the sales overview, customer segments, and data-quality audit. The dashboard supports country/date filters; changing them changes the displayed figures.

See [LICENSE-DATA.md](LICENSE-DATA.md) for dataset attribution.
