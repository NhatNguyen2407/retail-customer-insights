"""Interactive report for the public UCI Online Retail dataset."""
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics import key_metrics, monthly_revenue, rfm_customers, segment_summary, top_products
from src.data import clean_transactions, load_transactions

st.set_page_config(page_title="Retail Customer Insights", page_icon="🛍️", layout="wide")
st.title("Retail Customer Insights")
st.caption("A customer analytics case study · UCI Online Retail · December 2010 – December 2011")


@st.cache_data(show_spinner="Preparing the public dataset...")
def get_dataset():
    return load_transactions()


st.sidebar.header("Data source")
upload = st.sidebar.file_uploader("Optional: Online Retail.xlsx", type="xlsx")
try:
    if upload:
        sales, audit = clean_transactions(pd.read_excel(BytesIO(upload.getvalue())))
        st.sidebar.success("Using uploaded workbook")
    else:
        sales, audit = get_dataset()
        st.sidebar.success("Using UCI public dataset")
except Exception as error:
    st.error("Could not load the UCI dataset. Upload the workbook using the sidebar or check your connection.")
    st.code(str(error))
    st.stop()

if sales.empty:
    st.warning("There are no valid sales to analyse in this dataset.")
    st.stop()

st.sidebar.header("Filters")
all_countries = sorted(sales["country"].dropna().unique().tolist())
selected_countries = st.sidebar.multiselect("Countries", options=all_countries, default=all_countries)
start = sales["invoice_date"].min().date()
end = sales["invoice_date"].max().date()
chosen = st.sidebar.date_input("Date range", value=(start, end), min_value=start, max_value=end)
if not isinstance(chosen, tuple) or len(chosen) != 2:
    st.info("Choose a start and end date to continue.")
    st.stop()
from_date, to_date = chosen
filtered = sales.loc[
    sales["country"].isin(selected_countries)
    & sales["invoice_date"].dt.date.between(from_date, to_date)
].copy()
if filtered.empty:
    st.info("No transactions match these filters.")
    st.stop()

st.info("Revenue covers positive, non-cancelled sales only; returns and cancellations are excluded, not deducted. Currency: GBP (£).")
metrics = key_metrics(filtered)
cols = st.columns(4)
cols[0].metric("Sales revenue", f"£{metrics['revenue']:,.0f}")
cols[1].metric("Orders", f"{metrics['orders']:,}")
cols[2].metric("Average order value", f"£{metrics['aov']:,.2f}")
cols[3].metric("Known customers", f"{metrics['customers']:,}")

overview, customers, quality = st.tabs(["Sales overview", "Customer segments", "Data quality & methods"])
with overview:
    st.subheader("Monthly sales revenue")
    month = monthly_revenue(filtered)
    fig = px.line(month, x="month", y="revenue", markers=True, labels={"month": "Month", "revenue": "Revenue (£)"})
    fig.update_layout(margin=dict(t=25, b=0), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    left, right = st.columns(2)
    with left:
        st.subheader("Top countries by revenue")
        countries = filtered.groupby("country", as_index=False)["revenue"].sum().nlargest(10, "revenue")
        st.plotly_chart(px.bar(countries, x="revenue", y="country", orientation="h",
                               labels={"country": "Country", "revenue": "Revenue (£)"})
                        .update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=20, b=0)),
                        use_container_width=True)
    with right:
        st.subheader("Top products by revenue")
        products = top_products(filtered)
        st.dataframe(products[["description", "units", "revenue"]].rename(columns={
            "description": "Product", "units": "Units", "revenue": "Revenue (£)"}),
            hide_index=True, use_container_width=True)
with customers:
    st.subheader("RFM customer segmentation")
    st.caption("Recency, frequency and monetary scores are relative to the selected period and population. "
               "The observation date is one day after the latest selected purchase, not today.")
    rfm = rfm_customers(filtered)
    if rfm.empty:
        st.warning("No identified customer records in this selection.")
    else:
        summary = segment_summary(rfm)
        left, right = st.columns([1.1, 1])
        with left:
            st.plotly_chart(px.bar(summary, x="segment", y="customers", color="segment",
                                   labels={"segment": "Segment", "customers": "Customers"})
                            .update_layout(showlegend=False, margin=dict(t=20, b=0)), use_container_width=True)
        with right:
            st.plotly_chart(px.pie(summary, names="segment", values="revenue", hole=0.58,
                                   title="Revenue by segment"), use_container_width=True)
        st.dataframe(summary.round(2), hide_index=True, use_container_width=True)
        st.download_button("Export RFM customer table (CSV)", rfm.to_csv(index=False).encode(),
                           file_name="rfm-customers.csv", mime="text/csv")
        st.caption("'At risk' is a descriptive cohort label, not a validated churn prediction.")
with quality:
    st.subheader("Data quality audit (full source, before filters)")
    st.dataframe(pd.DataFrame([audit]).T.rename(columns={0: "Rows"}), use_container_width=True)
    st.markdown("""**Method:** Exclude cancellation invoices (prefix C), non-positive quantity/price, and invalid dates.

- Revenue is `Quantity × UnitPrice` in GBP; no refunds, shipping or tax adjustments.
- Customers without an ID remain in revenue and order KPIs but are excluded from RFM.
- Frequency counts distinct invoices; AOV = sales revenue / distinct invoices.
- Segments use relative 1–5 rank scores and transparent business rules, not ML predictions.
- Country/date filters affect every chart, metric, and RFM score.""")
    st.markdown("Source: [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) "
                "(Chen, 2015, CC BY 4.0; DOI: 10.24432/C5BW33).")
