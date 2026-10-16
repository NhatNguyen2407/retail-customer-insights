"""Revenue metrics and explainable RFM scoring."""
from __future__ import annotations

import pandas as pd


def key_metrics(sales: pd.DataFrame) -> dict[str, float | int]:
    """AOV uses distinct invoices, not individual product rows."""
    revenue = float(sales["revenue"].sum())
    order_count = int(sales["invoice_no"].nunique())
    return {
        "revenue": revenue,
        "orders": order_count,
        "aov": revenue / order_count if order_count else 0.0,
        "customers": int(sales["customer_id"].nunique()),
    }


def monthly_revenue(sales: pd.DataFrame) -> pd.DataFrame:
    df = sales.assign(month=sales["invoice_date"].dt.to_period("M").dt.to_timestamp())
    return df.groupby("month", as_index=False)["revenue"].sum()


def top_products(sales: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    return (
        sales.dropna(subset=["description"])
        .groupby(["stock_code", "description"], dropna=False, as_index=False)
        .agg(revenue=("revenue", "sum"), units=("quantity", "sum"))
        .nlargest(limit, "revenue")
    )


def rfm_customers(sales: pd.DataFrame) -> pd.DataFrame:
    """Rank each R/F/M component into 1–5; larger score is always better.

    The observation date is the day after the last transaction in the current
    selection, not today's date. RFM is recalculated for the filtered cohort.
    """
    known = sales.dropna(subset=["customer_id"])
    if known.empty:
        return pd.DataFrame(columns=[
            "customer_id", "recency", "frequency", "monetary",
            "r_score", "f_score", "m_score", "segment",
        ])
    reference = known["invoice_date"].max().normalize() + pd.Timedelta(days=1)
    result = (
        known.groupby("customer_id", as_index=False)
        .agg(last_purchase=("invoice_date", "max"),
             frequency=("invoice_no", "nunique"),
             monetary=("revenue", "sum"))
    )
    result["recency"] = (reference - result["last_purchase"].dt.normalize()).dt.days
    # Percentile ranks handle tied purchase counts without requiring unique bin edges.
    n = len(result)
    for column, score, ascending in (
        ("recency", "r_score", False),
        ("frequency", "f_score", True),
        ("monetary", "m_score", True),
    ):
        ranking = result[column].rank(method="average", ascending=ascending, pct=True)
        result[score] = ((ranking * 5).apply(lambda x: max(1, min(5, int(x + 0.999999)))))
    r, f, m = result["r_score"], result["f_score"], result["m_score"]
    result["segment"] = "Other"
    result.loc[(r >= 4) & (f <= 2), "segment"] = "New / promising"
    result.loc[(r <= 2) & (f >= 3), "segment"] = "At risk"
    result.loc[(r >= 3) & (f >= 4), "segment"] = "Loyal"
    result.loc[(r >= 4) & (f >= 4) & (m >= 4), "segment"] = "Champions"
    return result.drop(columns="last_purchase").sort_values("monetary", ascending=False)


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    if rfm.empty:
        return pd.DataFrame(columns=["segment", "customers", "revenue", "average_recency"])
    return (
        rfm.groupby("segment", as_index=False)
        .agg(customers=("customer_id", "size"), revenue=("monetary", "sum"),
             average_recency=("recency", "mean"))
        .sort_values("revenue", ascending=False)
    )
