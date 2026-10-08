import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(
    page_title="Indian Stock Fundamental & Governance Analyzer",
    page_icon="📈",
    layout="wide"
)

st.title("🇮🇳 Indian Long-Term Stock Fundamental & Governance Analyzer")
st.markdown("""
*Quantitative screens are your first filter. Always review annual reports, management integrity, and corporate governance before investing in Indian equities.*
""")

# Sidebar Input
st.sidebar.header("Stock Selection")
stock_input = st.sidebar.text_input("Enter NSE/BSE Symbol (e.g., STLTECH.NS, RELIANCE.NS, TCS.NS):", value="STLTECH.NS")
symbol = stock_input.strip().upper()

st.sidebar.markdown("---")
st.sidebar.header("Tier 2: Governance & Qualitative Audit Checklist")
st.sidebar.markdown("Verify these manually from the Annual Report / Screener.in before final allocation:")

pledged_shares = st.sidebar.checkbox("1. Promoter Pledged Shares < 5% / Zero?", value=True)
clean_rpt = st.sidebar.checkbox("2. Clean Related-Party Transactions (No suspicious loans/advances)?", value=True)
auditor_stability = st.sidebar.checkbox("3. Stable Auditor Track Record (No frequent sudden resignations)?", value=True)
skin_in_game = st.sidebar.checkbox("4. High Promoter Skin in the Game (> 40% or solid institutional backing)?", value=True)
economic_moat = st.sidebar.checkbox("5. Identifiable Economic Moat (Pricing power / Brand / Switching costs)?", value=True)

@st.cache_data(ttl=3600)
def fetch_stock_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info or {}
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        return info, financials, balance_sheet
    except Exception as e:
        return {}, None, None

if symbol:
    with st.spinner(f"Analyzing {symbol} via financial statements..."):
        info, financials, balance_sheet = fetch_stock_data(symbol)
        
    # Safe metadata extraction
    company_name = info.get('longName', info.get('shortName', symbol))
    current_price = info.get('currentPrice', info.get('regularMarketPrice', info.get('previousClose', 'N/A')))
    market_cap = info.get('marketCap', None)
    sector = info.get('sector', 'N/A')

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Company Name", company_name)
    col2.metric("Current Price", f"₹ {current_price}" if current_price != 'N/A' else 'N/A')
    col3.metric("Market Cap", f"₹ {market_cap / 1e7:,.2f} Cr" if market_cap else "N/A")
    col4.metric("Sector", sector)

    st.markdown("---")
    
    # --- ROBUST METRIC CALCULATION (ROCE, ROE, DEBT-TO-EQUITY) ---
    roce = info.get('returnOnCapitalEmployed', None)
    roe = info.get('returnOnEquity', None)
    debt_to_equity = info.get('debtToEquity', None)
    if debt_to_equity is not None and debt_to_equity > 10:  
        debt_to_equity = debt_to_equity / 100.0

    operating_margins = info.get('operatingMargins', None)
    
    # Fallback calculations from balance sheet & financials
    try:
        if balance_sheet is not None and not balance_sheet.empty:
            latest_col = balance_sheet.columns[0]
            
            # Equity lookup
            equity = None
            for eq_key in ['Stockholders Equity', 'Common Stock Equity', 'Total Equity Gross Minority Interest']:
                if eq_key in balance_sheet.index:
                    equity = balance_sheet.loc[eq_key][latest_col]
                    if equity and equity > 0:
                        break
            
            # Total Debt lookup
            total_debt = None
            for debt_key in ['Total Debt', 'Short Long Term Debt', 'Long Term Debt']:
                if debt_key in balance_sheet.index:
                    val = balance_sheet.loc[debt_key][latest_col]
                    if val and not pd.isna(val):
                        total_debt = val
                        break
            
            if total_debt is None:
                total_liab = None
                for liab_key in ['Total Liabilities Net Minority Interest', 'Total Liab']:
                    if liab_key in balance_sheet.index:
                        total_liab = balance_sheet.loc[liab_key][latest_col]
                        break
                current_liab = balance_sheet.loc['Current Liabilities'][latest_col] if 'Current Liabilities' in balance_sheet.index else 0
                if total_liab and current_liab:
                    total_debt = total_liab - current_liab

            # Calculate Debt-to-Equity if missing
            if debt_to_equity is None and total_debt is not None and equity and equity > 0:
                debt_to_equity = total_debt / equity

            # Fallback ROCE / ROE calculation
            if financials is not None and not financials.empty:
                fin_col = financials.columns[0]
                ebit = financials.loc['Operating Income'][fin_col] if 'Operating Income' in financials.index else None
                if ebit is None and 'EBIT' in financials.index:
                    ebit = financials.loc['EBIT'][fin_col]
                
                net_income = financials.loc['Net Income'][fin_col] if 'Net Income' in financials.index else None
                total_assets = balance_sheet.loc['Total Assets'][latest_col] if 'Total Assets' in balance_sheet.index else None
                
                if roce is None and ebit and total_assets and equity:
                    capital_employed = total_assets - (total_assets - equity - (total_debt or 0))
                    if capital_employed > 0:
                        roce = ebit / capital_employed
                
                if roe is None and net_income and equity and equity > 0:
                    roe = net_income / equity
    except Exception:
        pass

    # --- TIER 1: QUANTITATIVE FILTER (SCREENER METRICS) ---
    st.subheader("📊 Tier 1: Quantitative Filter (Financial Metrics)")
    
    q_score = 0
    q1, q2, q3, q4 = st.columns(4)
    
    with q1:
        st.markdown("**ROCE (Return on Capital)**")
        val_roce = f"{roce*100:.2f}%" if roce else "N/A"
        st.metric("ROCE", val_roce, "Target >= 15%")
        if roce and roce >= 0.15:
            q_score += 1
            st.success("✅ Passed (>=15%)")
        else:
            st.warning("⚠️ Below 15% or N/A")
            
    with q2:
        st.markdown("**ROE (Return on Equity)**")
        val_roe = f"{roe*100:.2f}%" if roe else "N/A"
        st.metric("ROE", val_roe, "Target >= 15%")
        if roe and roe >= 0.15:
            q_score += 1
            st.success("✅ Passed (>=15%)")
        else:
            st.warning("⚠️ Below 15% or N/A")
            
    with q3:
        st.markdown("**Debt-to-Equity Ratio**")
        val_de = f"{debt_to_equity:.2f}" if debt_to_equity is not None else "N/A"
        st.metric("Debt / Equity", val_de, "Target < 1.0")
        if debt_to_equity is not None and debt_to_equity < 1.0:
            q_score += 1
            st.success("✅ Passed (<1.0)")
        else:
            st.warning("⚠️ High Debt or N/A")
            
    with q4:
        st.markdown("**Operating Margin**")
        val_om = f"{operating_margins*100:.2f}%" if operating_margins else "N/A"
        st.metric("Operating Margin", val_om, "Positive / Stable")
        if operating_margins and operating_margins > 0.05:
            q_score += 1
            st.success("✅ Healthy")
        else:
            st.warning("⚠️ Low or N/A")

    quant_pass = (q_score >= 3)
    
    st.markdown("---")
    
    # --- TIER 2: GOVERNANCE & QUALITATIVE AUDIT ---
    st.subheader("🛡️ Tier 2: Governance & Qualitative Audit (The Crucial Safeguard)")
    
    gov_checks_passed = sum([pledged_shares, clean_rpt, auditor_stability, skin_in_game, economic_moat])
    
    g1, g2 = st.columns(2)
    with g1:
        st.markdown(f"""
        **Governance Verification Summary:**
        - **Promoter Pledges:** `{"Pass" if pledged_shares else "Fail/Review"}`
        - **Related-Party Transactions:** `{"Clean" if clean_rpt else "Flagged"}`
        - **Auditor Stability:** `{"Stable" if auditor_stability else "Frequent Changes"}`
        - **Skin in the Game:** `{"High" if skin_in_game else "Low"}`
        - **Economic Moat:** `{"Identified" if economic_moat else "Weak/Unclear"}`
        """)
        
    with g2:
        st.info(
            f"**Governance Score:** {gov_checks_passed} / 5 criteria met.\n\n"
            "Remember: Quantitative screens are your first filter. Always review annual reports, "
            "management integrity, and corporate governance before investing in Indian equities."
        )
        
    st.markdown("---")
    
    # --- FINAL VERDICT & INVESTMENT STANCE ---
    st.subheader("🎯 Long-Term Investment Verdict")
    
    if quant_pass and gov_checks_passed >= 4:
        st.success("🟢 **STRONG LONG-TERM COMPOUNDER**: This company has cleared both your quantitative filters and rigorous governance audit.")
    elif quant_pass and gov_checks_passed < 4:
        st.warning("🟡 **QUALITATIVE AUDIT REQUIRED**: Numbers look solid, but governance checkpoints are unmet or unchecked.")
    else:
        st.error("🔴 **HIGH RISK / AVOID**: The company fails key quantitative thresholds.")

    with st.expander("📖 Business Summary & Additional Metrics"):
        st.write(info.get('longBusinessSummary', 'No business summary available.'))
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("PE Ratio", info.get('trailingPE', 'N/A'))
        col_b.metric("PB Ratio", info.get('priceToBook', 'N/A'))
        col_c.metric("Dividend Yield", f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "N/A")
else:
    st.info("👈 Enter a valid Indian stock ticker symbol (e.g., `STLTECH.NS`, `RELIANCE.NS`) in the sidebar to begin analysis.")
