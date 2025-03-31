# IRR and MOIC Calculator Prototype using Streamlit

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.title("📈 Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

if uploaded_file:
    try:
        # Try loading available sheet names first
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names

        # Try auto-selecting the expected sheet, fallback to first
        target_sheet = "Schedule of investments"
        if target_sheet in sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
        else:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
            st.warning(f"Sheet '{target_sheet}' not found. Loaded first available sheet: '{sheet_names[0]}'")

        st.subheader("Raw Investment Data")
        st.dataframe(df)

        # Try to identify a date column dynamically
        possible_date_columns = [col for col in df.columns if "date" in col.lower() or "year" in col.lower()]
        date_column = None
        for col in possible_date_columns:
            try:
                df["Date"] = pd.to_datetime(df[col], errors="coerce")
                if df["Date"].notna().sum() > 0:
                    date_column = col
                    break
            except:
                continue

        if date_column is None:
            st.error("Could not find a valid date column. Please include a column like 'Year - Month - Day'.")
        else:
            # Filter out rows without valid dates
            df = df.dropna(subset=["Date"])

            # Calculate MOIC
            df["MOIC"] = df["Fair Value"] / df["Cost"]

            # IRR Calculation requires cash flows
            irr_data = df[["Date", "Cost", "Proceeds", "Fair Value"]].copy()
            irr_data["Outflow"] = -irr_data["Cost"]
            irr_data["Inflow"] = irr_data["Proceeds"] + irr_data["Fair Value"]
            
            cashflows = irr_data.groupby("Date").agg({"Outflow": "sum", "Inflow": "sum"})
            cashflows_sorted = cashflows.sort_index()
            cashflow_series = (cashflows_sorted["Outflow"] + cashflows_sorted["Inflow"]).tolist()

            if len(cashflow_series) >= 2:
                irr = np.irr(cashflow_series)
                irr_display = f"{irr * 100:.2f}%" if irr is not None else "N/A"
            else:
                irr_display = "Insufficient data"

            st.subheader("Summary Metrics")
            st.metric("Total Amount Invested", f"${df['Cost'].sum():,.2f}")
            st.metric("Total Fair Value", f"${df['Fair Value'].sum():,.2f}")
            st.metric("Portfolio MOIC", f"{(df['Fair Value'].sum() / df['Cost'].sum()):.2f}")
            st.metric("Estimated IRR", irr_display)

            st.subheader("MOIC by Investment")
            st.dataframe(df[["Investment Name", "Cost", "Fair Value", "MOIC"]].sort_values("MOIC", ascending=False))
    
    except Exception as e:
        st.error(f"Error loading file: {e}")
