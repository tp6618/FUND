import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Stock Fundamental Scoring Calculator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .stTextInput > div > div > input {
        background-color: #1e293b;
        color: #f8fafc;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    .metric-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .pass-badge {
        background-color: #065f46;
        color: #6ee7b7;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .fail-badge {
        background-color: #991b1b;
        color: #fca5a5;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .warning-badge {
        background-color: #92400e;
        color: #fde68a;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_stock_data(ticker_symbol):
    """
    Fetches financial statements, balance sheets, and key statistics
    using yfinance as a robust proxy for fundamental metrics.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        # Check if valid ticker by looking up basic info
        if not info or 'longName' not in info and 'shortName' not in info:
            return None, "Ticker not found or invalid symbol."
            
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        return {
            "info": info,
            "financials": financials,
            "balance_sheet": balance_sheet,
            "cashflow": cashflow
        }, None
    except Exception as e:
        return None, str(e)

def analyze_fundamentals(data):
    info = data["info"]
    financials = data["financials"]
    bs = data["balance_sheet"]
    cf = data["cashflow"]
    
    checks = []
    score = 0
    max_score = 6 * 10  # 6 categories, max 10 points each = 60 points total
    
    # 1. Return on Capital Employed (ROCE) / Return on Equity (ROE)
    roe = info.get("returnOnEquity", None)
    roe_val = roe * 100 if roe is not None else 0.0
    roe_score = 0
    if roe_val >= 20:
        roe_score = 10
        roe_status = "PASS"
        roe_note = f"Excellent ROE at {roe_val:.2f}% (Target: >= 20%)"
    elif roe_val >= 15:
        roe_score = 7
        roe_status = "PASS"
        roe_note = f"Good ROE at {roe_val:.2f}% (Target: >= 15%)"
    elif roe_val >= 10:
        roe_score = 4
        roe_status = "WARNING"
        roe_note = f"Moderate ROE at {roe_val:.2f}% (Below 15% ideal threshold)"
    else:
        roe_score = 0
        roe_status = "FAIL"
        roe_note = f"Low or negative ROE at {roe_val:.2f}%"
    
    score += roe_score
    checks.append({
        "category": "Profitability (ROE)",
        "metric": f"{roe_val:.2f}%",
        "target": ">= 15-20%",
        "status": roe_status,
        "points": f"{roe_score}/10",
        "note": roe_note
    })
    
    # 2. Leverage / Debt-to-Equity Ratio
    debt_to_equity = info.get("debtToEquity", None)
    # yfinance gives D/E in percentage sometimes or ratio depending on version (usually percentage e.g. 50 means 0.5)
    if debt_to_equity is not None:
        # Normalize if it's reported as percentage
        de_ratio = debt_to_equity / 100.0 if debt_to_equity > 5 else debt_to_equity
    else:
        de_ratio = 999.0
        
    de_score = 0
    if de_ratio <= 0.5:
        de_score = 10
        de_status = "PASS"
        de_note = f"Conservative leverage, D/E ratio at {de_ratio:.2f} (Target: < 1.0)"
    elif de_ratio <= 1.0:
        de_score = 7
        de_status = "PASS"
        de_note = f"Acceptable leverage, D/E ratio at {de_ratio:.2f} (Target: < 1.0)"
    elif de_ratio <= 2.0:
        de_score = 3
        de_status = "WARNING"
        de_note = f"Elevated leverage, D/E ratio at {de_ratio:.2f}"
    else:
        de_score = 0
        de_status = "FAIL"
        de_note = f"High debt load, D/E ratio at {de_ratio:.2f}"
        
    score += de_score
    checks.append({
        "category": "Balance Sheet Leverage (D/E)",
        "metric": f"{de_ratio:.2f}",
        "target": "< 1.0",
        "status": de_status,
        "points": f"{de_score}/10",
        "note": de_note
    })
    
    # 3. Interest Coverage Ratio (EBIT / Interest Expense)
    try:
        # Approximate from income statement if available
        ebit = financials.loc["Operating Income"].iloc[0] if "Operating Income" in financials.index else 0
        interest_exp = abs(financials.loc["Interest Expense"].iloc[0]) if "Interest Expense" in financials.index else 1
        interest_coverage = ebit / interest_exp if interest_exp > 0 else 10.0
    except Exception:
        interest_coverage = info.get("interestCoverage", 5.0)
        if interest_coverage is None:
            interest_coverage = 5.0
            
    ic_score = 0
    if interest_coverage >= 6.0:
        ic_score = 10
        ic_status = "PASS"
        ic_note = f"Robust interest coverage at {interest_coverage:.1f}x (Target: > 4x)"
    elif interest_coverage >= 4.0:
        ic_score = 8
        ic_status = "PASS"
        ic_note = f"Healthy interest coverage at {interest_coverage:.1f}x (Target: > 4x)"
    elif interest_coverage >= 2.0:
        ic_score = 4
        ic_status = "WARNING"
        ic_note = f"Moderate interest coverage at {interest_coverage:.1f}x"
    else:
        ic_score = 0
        ic_status = "FAIL"
        ic_note = f"Weak interest coverage at {interest_coverage:.1f}x (Risk of debt servicing)"
        
    score += ic_score
    checks.append({
        "category": "Interest Coverage Ratio",
        "metric": f"{interest_coverage:.1f}x",
        "target": ">= 4.0x",
        "status": ic_status,
        "points": f"{ic_score}/10",
        "note": ic_note
    })
    
    # 4. Free Cash Flow Generation
    try:
        operating_cf = cf.loc["Operating Cash Flow"].iloc[0] if "Operating Cash Flow" in cf.index else 0
        net_income = financials.loc["Net Income"].iloc[0] if "Net Income" in financials.index else 1
        fcf_conversion = operating_cf / net_income if net_income != 0 else 1.0
    except Exception:
        fcf_conversion = 1.0
        
    fcf_score = 0
    if fcf_conversion >= 1.0:
        fcf_score = 10
        fcf_status = "PASS"
        fcf_note = f"Strong cash conversion ratio at {fcf_conversion:.2f}x net income"
    elif fcf_conversion >= 0.7:
        fcf_score = 7
        fcf_status = "PASS"
        fcf_note = f"Acceptable cash conversion at {fcf_conversion:.2f}x net income"
    elif fcf_conversion >= 0.4:
        fcf_score = 4
        fcf_status = "WARNING"
        fcf_note = f"Sub-optimal cash conversion at {fcf_conversion:.2f}x net income"
    else:
        fcf_score = 0
        fcf_status = "FAIL"
        fcf_note = f"Poor cash conversion ({fcf_conversion:.2f}x), profits are not backed by cash"
        
    score += fcf_score
    checks.append({
        "category": "Earnings Quality & FCF",
        "metric": f"{fcf_conversion:.2f}x FCF/NI",
        "target": ">= 0.8x",
        "status": fcf_status,
        "points": f"{fcf_score}/10",
        "note": fcf_note
    })
    
    # 5. Profit Margins & Stability
    net_margin = info.get("profitMargins", 0.0) * 100
    margin_score = 0
    if net_margin >= 15:
        margin_score = 10
        margin_status = "PASS"
        margin_note = f"High net profit margin at {net_margin:.2f}% (Pricing power indicator)"
    elif net_margin >= 8:
        margin_score = 7
        margin_status = "PASS"
        margin_note = f"Healthy net profit margin at {net_margin:.2f}%"
    elif net_margin >= 3:
        margin_score = 4
        margin_status = "WARNING"
        margin_note = f"Thin net profit margin at {net_margin:.2f}%"
    else:
        margin_score = 0
        margin_status = "FAIL"
        margin_note = f"Very low or negative net profit margin at {net_margin:.2f}%"
        
    score += margin_score
    checks.append({
        "category": "Profit Margin Stability",
        "metric": f"{net_margin:.2f}%",
        "target": ">= 10%",
        "status": margin_status,
        "points": f"{margin_score}/10",
        "note": margin_note
    })
    
    # 6. Valuation Discipline (P/E Ratio vs Benchmark)
    pe_ratio = info.get("trailingPE", None)
    if pe_ratio is None:
        pe_ratio = info.get("forwardPE", 25.0)
    if pe_ratio is None or pe_ratio <= 0:
        pe_ratio = 35.0  # Default assumption for unpriced/loss-making or high growth
        
    pe_score = 0
    if pe_ratio <= 15:
        pe_score = 10
        pe_status = "PASS"
        pe_note = f"Attractive valuation P/E at {pe_ratio:.1f}x"
    elif pe_ratio <= 25:
        pe_score = 8
        pe_status = "PASS"
        pe_note = f"Fair valuation P/E at {pe_ratio:.1f}x"
    elif pe_ratio <= 40:
        pe_score = 4
        pe_status = "WARNING"
        pe_note = f"Rich valuation P/E at {pe_ratio:.1f}x, requires high growth execution"
    else:
        pe_score = 0
        pe_status = "FAIL"
        pe_note = f"Very expensive valuation P/E at {pe_ratio:.1f}x (High downside risk)"
        
    score += pe_score
    checks.append({
        "category": "Valuation Discipline (P/E)",
        "metric": f"{pe_ratio:.1f}x",
        "target": "< 25x",
        "status": pe_status,
        "points": f"{pe_score}/10",
        "note": pe_note
    })
    
    final_percentage = (score / max_score) * 100
    return score, max_score, final_percentage, checks

st.title("📈 Stock Fundamental Scoring Calculator")
st.markdown("Automate your long-term fundamental analysis checklist inspired by Screener.in metrics. Enter any stock ticker below (e.g., `AAPL`, `MSFT`, `RELIANCE.NS`, `TCS.NS`, `NVDA`) to instantly evaluate its financial health.")

# Sidebar Controls
st.sidebar.header("🔍 Search & Parameters")
ticker_input = st.sidebar.text_input("Enter Stock Ticker Symbol:", value="AAPL").strip().upper()
st.sidebar.markdown("---")
st.sidebar.markdown("""
### 📋 Long-Term Investor Rules:
1. **ROCE/ROE >= 15%**: High capital efficiency.
2. **Debt/Equity < 1.0**: Safe balance sheet.
3. **Interest Coverage > 4x**: Safe debt servicing.
4. **Positive FCF**: Real cash earnings.
5. **Net Margins >= 10%**: Pricing power.
6. **Reasonable P/E**: Margin of safety.
""")

if st.sidebar.button("Run Fundamental Analysis", type="primary"):
    if not ticker_input:
        st.warning("Please enter a valid stock ticker symbol.")
    else:
        with st.spinner(f"Fetching financial data and analyzing fundamentals for {ticker_input}..."):
            data, error = fetch_stock_data(ticker_input)
            
            if error:
                st.error(f"Error fetching data for `{ticker_input}`: {error}. Please verify the ticker symbol (e.g. use `.NS` for Indian stocks on NSE).")
            else:
                info = data["info"]
                company_name = info.get("longName", ticker_input)
                sector = info.get("sector", "N/A")
                industry = info.get("industry", "N/A")
                market_cap = info.get("marketCap", 0)
                current_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
                
                # Display Company Header
                st.markdown(f"## {company_name} (`{ticker_input}`)")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Current Price", f"${current_price:,.2f}" if current_price else "N/A")
                with col2:
                    market_cap_str = f"${market_cap / 1e9:.2f}B" if market_cap else "N/A"
                    st.metric("Market Cap", market_cap_str)
                with col3:
                    st.metric("Sector", sector)
                with col4:
                    st.metric("Industry", industry)
                
                st.markdown("---")
                
                # Run Analysis
                score, max_score, percentage, checks = analyze_fundamentals(data)
                
                # Overall Scorecard Banner
                st.subheader("🎯 Overall Fundamental Health Score")
                
                col_score_1, col_score_2 = st.columns([1, 2])
                with col_score_1:
                    st.markdown(f"""
                        <div style="background-color: #1e293b; padding: 24px; border-radius: 12px; text-align: center; border: 1px solid #334155;">
                            <h1 style="font-size: 3rem; margin: 0; color: {'#34d399' if percentage >= 70 else '#fbbf24' if percentage >= 50 else '#f87171'};">{score} / {max_score}</h1>
                            <p style="font-size: 1.2rem; margin-top: 8px; font-weight: 600;">{percentage:.1f}% Score</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col_score_2:
                    if percentage >= 75:
                        verdict = "🟢 **Strong Long-Term Compounder**: This company exhibits robust financial health, solid capital returns, and a resilient balance sheet that fits long-term investment criteria."
                    elif percentage >= 50:
                        verdict = "🟡 **Moderate / Mixed Fundamentals**: The business shows promise in several metrics but has specific areas of vulnerability (such as leverage or margins) requiring closer qualitative review."
                    else:
                        verdict = "🔴 **High Risk / Weak Fundamentals**: Multiple red flags detected across return ratios, debt levels, or cash generation. Exercise extreme caution."
                    st.info(verdict)
                    
                st.markdown("---")
                
                # Detailed Breakdown Checklist Table
                st.subheader("📋 Granular Checklist Breakdown")
                
                for check in checks:
                    status = check["status"]
                    if status == "PASS":
                        badge = '<span class="pass-badge">PASS</span>'
                    elif status == "WARNING":
                        badge = '<span class="warning-badge">WARNING</span>'
                    else:
                        badge = '<span class="fail-badge">FAIL</span>'
                        
                    st.markdown(f"""
                        <div style="background-color: #1e293b; padding: 16px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #334155; display: flex; justify-content: space-between; align-items: center;">
                            <div style="flex: 2;">
                                <strong style="font-size: 1.1rem; color: #f8fafc;">{check['category']}</strong><br/>
                                <span style="color: #94a3b8; font-size: 0.9rem;">{check['note']}</span>
                            </div>
                            <div style="flex: 1; text-align: center;">
                                <span style="color: #cbd5e1; font-size: 0.95rem;">Actual: <b>{check['metric']}</b></span><br/>
                                <span style="color: #64748b; font-size: 0.8rem;">Target: {check['target']}</span>
                            </div>
                            <div style="flex: 1; text-align: right;">
                                {badge}<br/>
                                <span style="color: #94a3b8; font-size: 0.85rem; margin-top: 4px; display: inline-block;">Points: {check['points']}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                st.markdown("---")
                st.success("Analysis complete! Remember that quantitative screens are only the first filter. Always verify management integrity, corporate governance, and the economic moat before allocating capital.")

else:
    # Initial landing screen info
    st.info("👈 Enter a stock ticker in the sidebar and click **Run Fundamental Analysis** to generate the score.")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("### 📊 Return Metrics")
        st.write("Evaluates ROCE & ROE to measure how efficiently management allocates capital to generate compounding profits.")
    with col_b:
        st.markdown("### 🛡️ Balance Sheet Safety")
        st.write("Checks debt-to-equity ratios and interest coverage to ensure the company can easily survive recessions and credit crunches.")
    with col_c:
        st.markdown("### 💰 Cash Generation")
        st.write("Compares operating cash flow with net earnings to weed out accounting gimmicks and ensure real cash earnings.")
