import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
import io

st.set_page_config(layout="wide", page_title="Investment Dashboard", page_icon="📊")

# Sidebar menu for export options
with st.sidebar:
    st.header("🗕️ Export Options")
    download_csv = st.button("📄 Download CSV")
    download_pdf = st.button("🩾 Download PDF")
    st.caption("Click a button to generate and download your export.")

st.title(":bar_chart: Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

# Realized / Unrealized filter
st.markdown("### :mag: Filter Investments")
realization_options = ["All", "Realized", "Unrealized"]
realization_filter = st.radio("Show Investments:", realization_options, horizontal=True)

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, sheet_name=0)
    df.columns = df.columns.str.strip()

    df["Investment Date"] = pd.to_datetime(df["Investment Date"], errors='coerce')
    df["Exit Date"] = pd.to_datetime(df["Exit Date"], errors='coerce')

    df = df.dropna(subset=["Investment Name", "Total Investment", "Fair Value"], how='any')

    if realization_filter == "Realized":
        df = df[df["Status"].str.lower() == "realized"]
    elif realization_filter == "Unrealized":
        df = df[df["Status"].str.lower() == "unrealized"]

    fund_filter = st.multiselect("Select Fund(s):", options=df["Fund"].dropna().unique(), default=list(df["Fund"].dropna().unique()))
    df = df[df["Fund"].isin(fund_filter)]

    search_term = st.text_input("Search by Company/Investment Name:")
    if search_term:
        df = df[df["Investment Name"].str.contains(search_term, case=False, na=False)]

    df["MOIC"] = df["Fair Value"] / df["Total Investment"]
    df["ROI"] = ((df["Fair Value"] - df["Total Investment"]) / df["Total Investment"]) * 100
    df["Holding Period"] = (datetime.now() - df["Investment Date"]).dt.days / 365.25
    df["Annualized ROI"] = ((1 + df["ROI"] / 100) ** (1 / df["Holding Period"]) - 1) * 100
    df["Annualized ROI"] = df["Annualized ROI"].replace([np.inf, -np.inf], np.nan)

    total_invested = df["Total Investment"].sum()
    total_fair_value = df["Fair Value"].sum()
    moic = total_fair_value / total_invested if total_invested else 0

    dpi = df[df["Status"].str.lower() == "realized"]["Fair Value"].sum() / total_invested if total_invested else 0
    tvpi = moic

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Invested", f"${total_invested:,.0f}")
    col2.metric("Fair Value", f"${total_fair_value:,.0f}")
    col3.metric("MOIC", f"{moic:.2f}x")
    col4.metric("DPI", f"{dpi:.2f}x")

    st.markdown("---")

    st.subheader("MOIC by Fund")
    moic_fund = df.groupby("Fund").apply(lambda x: x["Fair Value"].sum() / x["Total Investment"].sum()).reset_index(name="MOIC")
    st.plotly_chart(px.bar(moic_fund, x="Fund", y="MOIC", title="MOIC by Fund"), use_container_width=True)

    st.subheader("Annualized ROI by Fund")
    roi_fund = df.groupby("Fund")["Annualized ROI"].mean().reset_index()
    st.plotly_chart(px.bar(roi_fund, x="Fund", y="Annualized ROI", title="Annualized ROI by Fund"), use_container_width=True)

    st.subheader("Capital Allocation")
    cap_alloc = df.groupby("Fund")["Total Investment"].sum().reset_index()
    st.plotly_chart(px.pie(cap_alloc, names="Fund", values="Total Investment", title="Capital Allocation by Fund"), use_container_width=True)

    st.subheader("Investment Stage Breakdown")
    stage_data = df["Stage"].value_counts().reset_index()
    stage_data.columns = ["Stage", "Count"]
    st.plotly_chart(px.pie(stage_data, names="Stage", values="Count", title="Investments by Stage"), use_container_width=True)

    st.subheader("Cost vs Fair Value over Time")
    time_data = df.groupby(df["Investment Date"].dt.to_period("M")).agg({"Total Investment": "sum", "Fair Value": "sum"}).reset_index()
    time_data["Investment Date"] = time_data["Investment Date"].dt.to_timestamp()
    fig = px.line(time_data, x="Investment Date", y=["Total Investment", "Fair Value"], title="Cost vs Fair Value Over Time")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Portfolio Table")
    st.dataframe(df.sort_values(by="Fair Value", ascending=False).reset_index(drop=True), use_container_width=True)

    if download_csv:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv_data, file_name="filtered_investments.csv", mime="text/csv")

    if download_pdf:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Investment Dashboard Summary", ln=True, align='C')

        summary_text = [
            f"Total Invested: ${total_invested:,.0f}",
            f"Fair Value: ${total_fair_value:,.0f}",
            f"MOIC: {moic:.2f}x",
            f"DPI: {dpi:.2f}x",
            f"TVPI: {tvpi:.2f}x"
        ]

        for item in summary_text:
            pdf.cell(200, 10, txt=item, ln=True, align='L')

        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        st.download_button("Download PDF", data=pdf_output.getvalue(), file_name="investment_summary.pdf", mime="application/pdf")
