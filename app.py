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

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: #1f242d;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🇮🇳 Indian Long-Term Stock Fundamental & Governance Analyzer")
st.markdown("""
*Quantitative screens are your first filter. Always review annual reports, management integrity, and corporate governance before investing in Indian equities.*
""")

# Sidebar Input
st.sidebar.header("Stock Selection")
default_stocks = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", 
    "ITC.NS", "LT.NS", "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", 
    "ASIANPAINT.NS", "TITAN.NS", "BAJFINANCE.NS", "MARUTI.NS"
]

stock_input = st.sidebar.text_input("Enter NSE/BSE Symbol (e.g., RELIANCE.NS, TCS.NS, TATAMOTORS.NS):", value="RELIANCE.NS")
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
def fetch_stock_info(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        return info
    except Exception as e:
        return None

if symbol:
    with st.spinner(f"Fetching data and running quantitative filter for {symbol}..."):
        info = fetch_stock_info(symbol)
        
    if not info or 'longName' not in info:
        st.error(f"Could not retrieve data for `{symbol}`. Please check if the ticker symbol is correct (e.g., must end with `.NS` for NSE or `.BO` for BSE).")
    else:
        # Display Basic Company Info
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Company Name", info.get('longName', symbol))
        col2.metric("Current Price", f"₹ {info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))}")
        col3.metric("Market Cap", f"₹ {info.get('marketCap', 0) / 1e7:,.2f} Cr" if info.get('marketCap') else "N/A")
        col4.metric("Sector", info.get('sector', 'N/A'))

        st.markdown("---")
        
        # --- TIER 1: QUANTITATIVE FILTER (SCREENER METRICS) ---
        st.subheader("📊 Tier 1: Quantitative Filter (Financial Metrics)")
        
        # Extract key metrics safely
        roce = info.get('returnOnCapitalEmployed', None)
        roe = info.get('returnOnEquity', None)
        debt_to_equity = info.get('debtToEquity', None)
        if debt_to_equity is not None:
            debt_to_equity = debt_to_equity / 100.0 # yfinance often returns D/E as percentage or ratio
            
        profit_margins = info.get('profitMargins', None)
        operating_margins = info.get('operatingMargins', None)
        
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
            st.success("🟢 **STRONG LONG-TERM COMPOUNDER**: This company has cleared both your quantitative filters and rigorous governance audit. Suitable for deeper due diligence and phased long-term accumulation.")
        elif quant_pass and gov_checks_passed < 4:
            st.warning("🟡 **QUALITATIVE AUDIT REQUIRED**: While the numbers look solid on Screener, governance or qualitative checkpoints are unmet or unchecked. **Do not invest** until you personally review the annual report notes for related-party transactions and promoter pledges.")
        else:
            st.error("🔴 **HIGH RISK / AVOID**: The company fails key quantitative thresholds (ROCE/Debt/Margins). Exercise extreme caution or discard from your long-term watch-list.")

        # Additional Company Summary Info
        with st.expander("📖 Business Summary & Additional Metrics"):
            st.write(info.get('longBusinessSummary', 'No business summary available.'))
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("PE Ratio", info.get('trailingPE', 'N/A'))
            col_b.metric("PB Ratio", info.get('priceToBook', 'N/A'))
            col_c.metric("Dividend Yield", f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "N/A")
else:
    st.info("👈 Enter a valid Indian stock ticker symbol (e.g., `RELIANCE.NS`, `TCS.NS`) in the sidebar to begin analysis.")
