import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
px.defaults.template = "plotly_white"
from datetime import datetime
from fpdf import FPDF
import io


def format_currency(x):
    return f"${x:,.0f}" if pd.notnull(x) else "N/A"

def format_percent(x, decimals=2):
    return f"{x:.{decimals}%}" if pd.notnull(x) else "N/A"

def format_multiple(x):
    return f"{x:.2f}x" if pd.notnull(x) else "N/A"

st.set_page_config(layout="wide", page_title="Investment Dashboard", page_icon="📊")

# Sidebar menu for export options
with st.sidebar:
    st.header("🗕️ Export Options")
    download_csv = st.button("📄 Download CSV")
    download_pdf = st.button("🩾 Download PDF")
    st.caption("Click a button to generate and download your export.")

st.title(":bar_chart: Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

# --- Manual Entry Form ---
# --- Manual Entry Form ---
with st.expander("➕ Add Investment Manually", expanded=True):
    if "manual_entries" not in st.session_state:
        st.session_state.manual_entries = []

    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        with col1:
            investment_name = st.text_input("Investment Name")
            fund_name = st.text_input("Fund Name")
            cost = st.number_input("Cost", min_value=0.0, step=1000.0)
        with col2:
            fair_value = st.number_input("Fair Value", min_value=0.0, step=1000.0)
            date = st.date_input("Date", value=datetime.today())
            status = st.selectbox("Realized / Unrealized", ["Unrealized", "Realized"])
        
        submitted = st.form_submit_button("Add Investment")

        if submitted:
            new_entry = {
                "Investment Name": investment_name,
                "Fund Name": fund_name,
                "Cost": cost,
                "Fair Value": fair_value,
                "Date": pd.to_datetime(date),
                "Realized / Unrealized": status
            }
            st.session_state.manual_entries.append(new_entry)
            st.success(f"Added investment: {investment_name}")

    # 👇 This is OUTSIDE the form block now
    if st.session_state.manual_entries:
        st.markdown("#### Manually Added Investments")
        st.dataframe(pd.DataFrame(st.session_state.manual_entries))

        if st.button("🧹 Clear Manual Entries"):
            st.session_state.manual_entries = []
            st.success("Manual entries cleared.")

    if st.session_state.manual_entries:
        st.markdown("#### Manually Added Investments")
        st.dataframe(pd.DataFrame(st.session_state.manual_entries))

        if st.button("🧹 Clear Manual Entries"):
            st.session_state.manual_entries = []
            st.success("Manual entries cleared.")
    st.session_state.manual_entries.append(new_entry)
    st.success(f"Added investment: {investment_name}")
        if st.session_state.manual_entries:
        st.markdown("#### Manually Added Investments")
        st.dataframe(pd.DataFrame(st.session_state.manual_entries))
            if st.button("🧹 Clear Manual Entries"):
        st.session_state.manual_entries = []
        st.success("Manual entries cleared.")

# Realized / Unrealized filter
st.markdown("### :mag: Filter Investments")
realization_options = ["All", "Realized", "Unrealized"]
realization_filter = st.radio("Show Investments:", realization_options, horizontal=True)

if uploaded_file is not None:
    df_excel = pd.read_excel(uploaded_file)
    df_manual = pd.DataFrame(st.session_state.manual_entries)
    df = pd.concat([df_excel, df_manual], ignore_index=True)
    df.columns = df.columns.str.strip()  # Strip extra whitespace from headers

    required_columns = ["Investment Name", "Cost", "Fair Value", "Date", "Fund Name"]
    if not all(col in df.columns for col in required_columns):
        st.error("Missing required columns in uploaded file. Please ensure headers match expected structure.")
    else:
        df = df.dropna(subset=["Cost", "Fair Value", "Date"])
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])

        df["MOIC"] = df["Fair Value"] / df["Cost"]

        today = pd.Timestamp.today()
        df["ROI"] = (df["Fair Value"] - df["Cost"]) / df["Cost"]
        df["Years Held"] = (today - df["Date"]).dt.days / 365.25
        df["Annualized ROI"] = df.apply(
            lambda row: (row["MOIC"] ** (1 / row["Years Held"]) - 1) if row["Years Held"] > 0 else np.nan,
            axis=1
        )

        unique_funds = sorted(df["Fund Name"].dropna().unique())
        selected_funds = st.multiselect("Select Fund(s)", options=unique_funds, default=unique_funds, key="fund_selector")

        # Apply filters (FIXED + DEBUGGED)
        df_filtered = df.copy()

        # Apply Realized/Unrealized filter
        if "Realized / Unrealized" in df_filtered.columns:
            df_filtered["Realized / Unrealized"] = df_filtered["Realized / Unrealized"].astype(str).str.strip().str.lower()
            if realization_filter != "All":
                realization_filter_lower = realization_filter.lower()
                df_filtered = df_filtered[df_filtered["Realized / Unrealized"] == realization_filter_lower]

        # Apply Fund Name filter
        df_filtered = df_filtered[df_filtered["Fund Name"].isin(selected_funds)]

        df_filtered = df_filtered.reset_index(drop=True)

        # 🔍 Add search bar for investment name
        search_term = st.text_input("Search Investments by Name")
        if search_term:
            df_filtered = df_filtered[df_filtered["Investment Name"].str.contains(search_term, case=False, na=False)]

        if df_filtered.empty:
            st.warning("No investments match the selected filters.")
        else:
            total_invested = df_filtered["Cost"].sum()
            total_fair_value = df_filtered["Fair Value"].sum()
            portfolio_moic = total_fair_value / total_invested if total_invested != 0 else 0
            portfolio_roi = (total_fair_value - total_invested) / total_invested
            total_days = (today - df_filtered["Date"].min()).days
            df_filtered["Weighted Annualized ROI Contribution"] = df_filtered.apply(
                lambda row: row["Annualized ROI"] * row["Cost"] if pd.notnull(row["Annualized ROI"]) else 0,
                axis=1
            )
            portfolio_annualized_roi = df_filtered["Weighted Annualized ROI Contribution"].sum() / df_filtered["Cost"].sum()

            st.markdown("### :bar_chart: Summary")
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total Amount Invested", format_currency(total_invested), help="Sum of all capital deployed across filtered investments.")
            col2.metric("Total Fair Value", format_currency(total_fair_value), help="Current estimated value of all filtered investments.")
            col3.metric("Portfolio MOIC", format_multiple(portfolio_moic), help="Multiple on Invested Capital (Fair Value / Cost)")
            col4.metric("Portfolio-Level ROI", format_percent(portfolio_annualized_roi, 1), help="Annualized return across all investments, weighted by capital")

            realized_df = df_filtered[df_filtered["Realized / Unrealized"] == "realized"] if "Realized / Unrealized" in df_filtered.columns else pd.DataFrame()
            unrealized_df = df_filtered[df_filtered["Realized / Unrealized"] == "unrealized"] if "Realized / Unrealized" in df_filtered.columns else pd.DataFrame()

            realized_distributions = realized_df["Fair Value"].sum() if not realized_df.empty else 0
            residual_value = unrealized_df["Fair Value"].sum() if not unrealized_df.empty else 0
            dpi = realized_distributions / total_invested if total_invested != 0 else np.nan
            tvpi = (realized_distributions + residual_value) / total_invested if total_invested != 0 else np.nan

            col5.metric("DPI", format_multiple(dpi), help="Distributed to Paid-In Capital: Realized cash returns relative to total invested")
            
            st.markdown("---")
            
            st.subheader(":bar_chart: Portfolio MOIC by Fund")
            moic_by_fund = df_filtered.groupby("Fund Name").apply(lambda x: x["Fair Value"].sum() / x["Cost"].sum()).reset_index(name="Portfolio MOIC")
            moic_by_fund["MOIC Label"] = moic_by_fund["Portfolio MOIC"].round(2).astype(str) + "x"
            fig1 = px.bar(moic_by_fund, x="Fund Name", y="Portfolio MOIC", title="MOIC per Fund", text="MOIC Label")
            st.plotly_chart(fig1, use_container_width=True)

            st.subheader(":chart_with_upwards_trend: Annualized ROI by Fund")
            roi_fund = df_filtered.groupby("Fund Name").apply(
                lambda x: np.average(x["Annualized ROI"], weights=x["Cost"]) if x["Cost"].sum() > 0 else np.nan
            ).reset_index(name="Weighted Annualized ROI")
            roi_fund["Annualized ROI Label"] = roi_fund["Weighted Annualized ROI"].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
            fig2 = px.bar(
                roi_fund,
                x="Fund Name",
                y="Weighted Annualized ROI",
                title="Weighted Annualized ROI per Fund",
                text="Annualized ROI Label"
            )
            st.plotly_chart(fig2, use_container_width=True)

            st.subheader(":moneybag: Capital Allocation by Fund")
            pie_df = df_filtered.groupby("Fund Name")["Cost"].sum().reset_index()
            fig3 = px.pie(pie_df, names="Fund Name", values="Cost", title="Capital Invested per Fund")
            st.plotly_chart(fig3, use_container_width=True)

            if "Stage" in df_filtered.columns:
                st.subheader(":dna: Investments by Stage")
                stage_df = df_filtered.groupby("Stage")["Cost"].sum().reset_index()
                fig4 = px.pie(stage_df, names="Stage", values="Cost", title="Investments by Stage")
                st.plotly_chart(fig4, use_container_width=True)

            if not search_term:
                st.subheader(":bar_chart: Cost Basis vs Fair Value Since Inception")
                chart_mode = st.selectbox("Chart Mode", ["Cumulative", "Monthly Deployed"], index=0)
                if chart_mode == "Cumulative":
                    df_filtered["Date Group"] = df_filtered["Date"].dt.to_period("M").dt.to_timestamp()
                    cost_value_df = df_filtered.groupby("Date Group")[["Cost", "Fair Value"]].sum().sort_index().cumsum().reset_index()
                    fig_cost_value = px.line(cost_value_df, x="Date Group", y=["Cost", "Fair Value"], title="Cumulative Cost vs Fair Value Over Time", )
                    st.plotly_chart(fig_cost_value, use_container_width=True)
                else:
                    df_filtered["Month"] = df_filtered["Date"].dt.to_period("M").dt.to_timestamp()
                    monthly_df = df_filtered.groupby("Month")["Cost"].sum().reset_index()
                    fig_deployed = px.bar(monthly_df, x="Month", y="Cost", title="Monthly Deployed", )
                    st.plotly_chart(fig_deployed, use_container_width=True)
            else:
                st.subheader(":bar_chart: Cost vs Fair Value (Filtered View)")
                search_chart_df = df_filtered.groupby("Investment Name")[["Cost", "Fair Value"]].sum().reset_index().melt(
                    id_vars="Investment Name",
                    var_name="Metric",
                    value_name="Amount"
                )
                fig_bar_filtered = px.bar(
                    search_chart_df,
                    x="Investment Name",
                    y="Amount",
                    color="Metric",
                    barmode="group",
                    title="Cost vs Fair Value for Selected Investments",
                    
                )
                st.plotly_chart(fig_bar_filtered, use_container_width=True)

            # 💰 Top Value Creators (by $ gain)
            df_filtered["$ Gain"] = df_filtered["Fair Value"] - df_filtered["Cost"]
            top_gainers = df_filtered.sort_values("$ Gain", ascending=False).head(3)["Investment Name"].tolist()

            # 📉 Biggest Losses (by $ loss)
            df_filtered["$ Loss"] = df_filtered["Cost"] - df_filtered["Fair Value"]
            df_filtered_loss_only = df_filtered[df_filtered["$ Loss"] > 0]
            top_losers = df_filtered_loss_only.sort_values("$ Loss", ascending=False).head(3)["Investment Name"].tolist()

            # 🏋️ Highest Conviction (by Cost)
            top_allocations = df_filtered.sort_values("Cost", ascending=False).head(3)["Investment Name"].tolist()

            # ⚡ Most Efficient (low cost, high ROI)
            efficient_df = df_filtered[df_filtered["Cost"] < df_filtered["Cost"].median()]  # small bets
            efficient_df = efficient_df[efficient_df["Annualized ROI"].notnull()]
            top_efficient = efficient_df.sort_values("Annualized ROI", ascending=False).head(3)["Investment Name"].tolist()

            st.markdown(f"**💰 Largest Value Gains:** {', '.join(top_gainers)}")
            st.markdown(f"**📉 Largest Losses:** {', '.join(top_losers) if top_losers else 'None'}")
            st.markdown(f"**🏋️ Highest Conviction Bets:** {', '.join(top_allocations)}")
            st.markdown(f"**⚡ Most Efficient Bets:** {', '.join(top_efficient)}")

            def highlight(val):
                return "background-color: #ffe6e6" if isinstance(val, float) and val < 0 else ""

            st.markdown(f"### :abacus: Investment Table – Investments in View: {len(df_filtered)}")
            df_filtered["MOIC"] = df_filtered["MOIC"].round(2).astype(str) + "x"
            df_filtered_display = df_filtered.copy()
            df_filtered_display["Cost"] = df_filtered_display["Cost"].apply(lambda x: f"${x:,.0f}")
            df_filtered_display["Fair Value"] = df_filtered_display["Fair Value"].apply(lambda x: f"${x:,.0f}")
            df_filtered_display["ROI"] = df_filtered_display["ROI"].apply(lambda x: f"{x:.2%}")
            df_filtered_display["Annualized ROI"] = df_filtered_display["Annualized ROI"].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "N/A")
            summary_row = pd.DataFrame({
                "Investment Name": ["Total"],
                "Fund Name": ["-"],
                "Cost": [f"${df_filtered['Cost'].sum():,.0f}"],
                "Fair Value": [f"${df_filtered['Fair Value'].sum():,.0f}"],
                "MOIC": [f"{portfolio_moic:.2f}x"],
                "ROI": [f"{portfolio_roi:.2%}"],
                "Annualized ROI": [f"{portfolio_annualized_roi:.2%}" if not np.isnan(portfolio_annualized_roi) else "N/A"]
            })
            df_with_total = pd.concat([
                df_filtered_display[["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC", "ROI", "Annualized ROI"]],
                summary_row
            ], ignore_index=True)
            def style_moic(val):
                try:
                    val_float = float(val.replace("x", ""))
                    if val_float >= 2:
                        return "background-color: #d4edda"  # green
                    elif val_float >= 1:
                        return "background-color: #fff3cd"  # yellow
                    else:
                        return "background-color: #f8d7da"  # red
                except:
                    return ""

            def style_roi(val):
                try:
                    val_float = float(val.strip('%')) / 100
                    if val_float >= 0.20:
                        return "background-color: #d4edda"
                    elif val_float >= 0.10:
                        return "background-color: #fff3cd"
                    else:
                        return "background-color: #f8d7da"
                except:
                    return ""

            styled_df = df_with_total.style.applymap(style_moic, subset=["MOIC"]).applymap(style_roi, subset=["ROI"])
            st.dataframe(styled_df)

            if download_csv:
                csv = df_filtered.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Click to Save CSV", data=csv, file_name="investment_summary.csv", mime="text/csv")

            if download_pdf:
                from PIL import Image
                import plotly.io as pio
                import os
                import tempfile

                pio.kaleido.scope.default_format = "png"

                buffer_dir = tempfile.mkdtemp()
                chart_paths = []
                chart_titles = ["MOIC by Fund", "Annualized ROI by Fund", "Capital Allocation", "Stage Breakdown", "Cost vs Fair Value Over Time" ]

                figs = [fig1, fig2, fig3, fig4 if 'fig4' in locals() else None, fig_cost_value if 'fig_cost_value' in locals() else None]

                for i, fig in enumerate(figs):
                    if fig:
                        path = os.path.join(buffer_dir, f"chart_{i}.png")
                        pio.write_image(fig, path, format='png', width=1000, height=600)
                        chart_paths.append((chart_titles[i], path))

                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                

                # Cover
                pdf.set_font("Arial", 'B', 20)
                pdf.set_text_color(30, 30, 30)
                pdf.cell(200, 20, txt="Investment Dashboard Report", ln=True, align="C")
                pdf.ln(10)

                # Summary
                pdf.set_font("Arial", '', 12)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 10, txt=f"Total Invested: ${total_invested:,.0f}", ln=True)
                pdf.cell(0, 10, txt=f"Total Fair Value: ${total_fair_value:,.0f}", ln=True)
                pdf.cell(0, 10, txt=f"Portfolio MOIC: {portfolio_moic:.2f}x", ln=True)
                pdf.cell(0, 10, txt=f"Annualized ROI: {portfolio_annualized_roi:.2%}", ln=True)
                pdf.cell(0, 10, txt=f"DPI: {dpi:.2f}x" if not np.isnan(dpi) else "DPI: N/A", ln=True)
                pdf.ln(5)

                pdf.set_font("Arial", 'I', 10)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 10, txt=f"Filtered Funds: {', '.join(selected_funds)}", ln=True)
                pdf.cell(0, 10, txt=f"Investment Status: {realization_filter}", ln=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(10)

                for i in range(0, len(chart_paths), 2):
                    pdf.add_page()
                    charts = chart_paths[i:i+2]
                    for j, (title, path) in enumerate(charts):
                        pdf.set_font("Arial", 'B', 14)
                        y_offset = 10 + j * 140
                        pdf.set_y(y_offset)
                        pdf.cell(0, 10, title, ln=True)
                        pdf.image(path, x=10, y=y_offset + 10, w=180)
                    pdf.ln(8)

                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, "Investment Table", ln=True)
                pdf.set_font("Arial", '', 10)
                col_headers = ["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC", "Annualized ROI"]
                col_widths = [40, 50, 25, 30, 20, 45]
                for i, header in enumerate(col_headers):
                    pdf.cell(col_widths[i], 10, header, border=1)
                pdf.ln()
                for _, row in df_with_total.iterrows():
                    for i, col in enumerate(col_headers):
                        cell_text = str(row[col])[:20]
                        bg_color = None

                        if col == "MOIC":
                            try:
                                moic_val = float(row[col].replace("x", ""))
                                if moic_val >= 2:
                                    bg_color = (212, 237, 218)  # green
                                elif moic_val >= 1:
                                    bg_color = (255, 243, 205)  # yellow
                                else:
                                    bg_color = (248, 215, 218)  # red
                            except:
                                pass

                        if col == "Annualized ROI":
                            try:
                                roi_val = float(row[col].replace("%", "")) / 100
                                if roi_val >= 0.20:
                                    bg_color = (212, 237, 218)
                                elif roi_val >= 0.10:
                                    bg_color = (255, 243, 205)
                                else:
                                    bg_color = (248, 215, 218)
                            except:
                                pass

                        if bg_color:
                            pdf.set_fill_color(*bg_color)
                            pdf.cell(col_widths[i], 10, cell_text, border=1, fill=True)
                        else:
                            pdf.cell(col_widths[i], 10, cell_text, border=1)
                    pdf.ln()

                pdf_output = os.path.join(buffer_dir, "investment_report.pdf")
                pdf.output(pdf_output)

                with open(pdf_output, "rb") as f:
                    st.download_button("⬇️ Download PDF Report", data=f, file_name="investment_report.pdf", mime="application/pdf")
