import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Indian Stock Fundamental Scoring Calculator",
    page_icon="🇮🇳",
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
def fetch_indian_stock_data(ticker_symbol):
    """
    Fetches financial statements, balance sheets, and key statistics
    for Indian stocks (NSE/BSE) using yfinance. Automatically appends .NS if missing.
    """
    clean_ticker = ticker_symbol.strip().upper()
    if not clean_ticker.endswith(".NS") and not clean_ticker.endswith(".BO"):
        query_symbol = clean_ticker + ".NS"
    else:
        query_symbol = clean_ticker
        
    try:
        stock = yf.Ticker(query_symbol)
        info = stock.info
        
        # Validate ticker existence
        if not info or ('longName' not in info and 'shortName' not in info):
            # Try BSE fallback if NS failed
            if query_symbol.endswith(".NS"):
                query_symbol = clean_ticker + ".BO"
                stock = yf.Ticker(query_symbol)
                info = stock.info
                if not info or ('longName' not in info and 'shortName' not in info):
                    return None, f"Ticker '{ticker_symbol}' not found on NSE/BSE."
            else:
                return None, f"Ticker '{ticker_symbol}' not found on NSE/BSE."
            
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow
        
        return {
            "symbol": query_symbol,
            "info": info,
            "financials": financials,
            "balance_sheet": balance_sheet,
            "cashflow": cashflow
        }, None
    except Exception as e:
        return None, str(e)

def analyze_indian_fundamentals(data):
    info = data["info"]
    financials = data["financials"]
    bs = data["balance_sheet"]
    cf = data["cashflow"]
    
    checks = []
    score = 0
    max_score = 7 * 10  # 7 rigorous criteria, max 10 points each = 70 points total
    
    # 1. Return on Equity (ROE) / ROCE proxy
    roe = info.get("returnOnEquity", None)
    roe_val = roe * 100 if roe is not None else 0.0
    roe_score = 0
    if roe_val >= 20:
        roe_score = 10
        roe_status = "PASS"
        roe_note = f"Elite return on equity at {roe_val:.2f}% (Target: >= 20%)"
    elif roe_val >= 15:
        roe_score = 7
        roe_status = "PASS"
        roe_note = f"Healthy ROE at {roe_val:.2f}% (Target: >= 15%)"
    elif roe_val >= 10:
        roe_score = 4
        roe_status = "WARNING"
        roe_note = f"Moderate ROE at {roe_val:.2f}% (Below 15% threshold)"
    else:
        roe_score = 0
        roe_status = "FAIL"
        roe_note = f"Low or negative ROE at {roe_val:.2f}%"
    
    score += roe_score
    checks.append({
        "category": "Capital Efficiency (ROE)",
        "metric": f"{roe_val:.2f}%",
        "target": ">= 15-20%",
        "status": roe_status,
        "points": f"{roe_score}/10",
        "note": roe_note
    })
    
    # 2. Debt-to-Equity Ratio
    debt_to_equity = info.get("debtToEquity", None)
    if debt_to_equity is not None:
        de_ratio = debt_to_equity / 100.0 if debt_to_equity > 5 else debt_to_equity
    else:
        de_ratio = 0.5  # default conservative assumption if missing
        
    de_score = 0
    if de_ratio <= 0.5:
        de_score = 10
        de_status = "PASS"
        de_note = f"Virtually debt-free or low debt, D/E at {de_ratio:.2f} (Target: < 1.0)"
    elif de_ratio <= 1.0:
        de_score = 7
        de_status = "PASS"
        de_note = f"Acceptable balance sheet leverage, D/E at {de_ratio:.2f} (Target: < 1.0)"
    elif de_ratio <= 2.0:
        de_score = 3
        de_status = "WARNING"
        de_note = f"Elevated debt load, D/E at {de_ratio:.2f}"
    else:
        de_score = 0
        de_status = "FAIL"
        de_note = f"Heavy debt burden, D/E at {de_ratio:.2f}"
        
    score += de_score
    checks.append({
        "category": "Balance Sheet Leverage (D/E)",
        "metric": f"{de_ratio:.2f}",
        "target": "< 1.0",
        "status": de_status,
        "points": f"{de_score}/10",
        "note": de_note
    })
    
    # 3. Interest Coverage Ratio
    try:
        ebit = financials.loc["Operating Income"].iloc[0] if "Operating Income" in financials.index else 0
        interest_exp = abs(financials.loc["Interest Expense"].iloc[0]) if "Interest Expense" in financials.index else 1
        interest_coverage = ebit / interest_exp if interest_exp > 0 else 8.0
    except Exception:
        interest_coverage = info.get("interestCoverage", 6.0)
        if interest_coverage is None:
            interest_coverage = 6.0
            
    ic_score = 0
    if interest_coverage >= 6.0:
        ic_score = 10
        ic_status = "PASS"
        ic_note = f"Robust interest coverage at {interest_coverage:.1f}x (Target: > 4x)"
    elif interest_coverage >= 4.0:
        ic_score = 8
        ic_status = "PASS"
        ic_note = f"Comfortable interest coverage at {interest_coverage:.1f}x (Target: > 4x)"
    elif interest_coverage >= 2.0:
        ic_score = 4
        ic_status = "WARNING"
        ic_note = f"Moderate interest coverage at {interest_coverage:.1f}x"
    else:
        ic_score = 0
        ic_status = "FAIL"
        ic_note = f"Fragile interest coverage at {interest_coverage:.1f}x (High debt servicing risk)"
        
    score += ic_score
    checks.append({
        "category": "Interest Coverage Ratio",
        "metric": f"{interest_coverage:.1f}x",
        "target": ">= 4.0x",
        "status": ic_status,
        "points": f"{ic_score}/10",
        "note": ic_note
    })
    
    # 4. Operating & Net Profit Margins
    net_margin = info.get("profitMargins", 0.0) * 100
    margin_score = 0
    if net_margin >= 15:
        margin_score = 10
        margin_status = "PASS"
        margin_note = f"Strong net profit margin at {net_margin:.2f}% (Indicates pricing power)"
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
        "category": "Net Profit Margin",
        "metric": f"{net_margin:.2f}%",
        "target": ">= 10%",
        "status": margin_status,
        "points": f"{margin_score}/10",
        "note": margin_note
    })
    
    # 5. Free Cash Flow (FCF) Conversion
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
        fcf_note = f"Excellent cash conversion at {fcf_conversion:.2f}x net income (Real cash earnings)"
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
        "category": "Earnings Quality (FCF / NI)",
        "metric": f"{fcf_conversion:.2f}x",
        "target": ">= 0.8x",
        "status": fcf_status,
        "points": f"{fcf_score}/10",
        "note": fcf_note
    })
    
    # 6. Promoter / Insider Holding
    insider_pct = info.get("heldPercentInsiders", 0.0) * 100
    if insider_pct == 0.0:
        insider_pct = info.get("heldPercentInstitutions", 50.0) # Proxy fallback if insider field missing
        promoter_note = f"Institutional/Promoter holding proxy at {insider_pct:.1f}%"
    else:
        promoter_note = f"Promoter/Insider holding at {insider_pct:.1f}% (Skin in the game)"
        
    promoter_score = 0
    if insider_pct >= 40:
        promoter_score = 10
        promoter_status = "PASS"
    elif insider_pct >= 25:
        promoter_score = 7
        promoter_status = "PASS"
    elif insider_pct >= 15:
        promoter_score = 4
        promoter_status = "WARNING"
    else:
        promoter_score = 0
        promoter_status = "FAIL"
        
    score += promoter_score
    checks.append({
        "category": "Promoter & Insider Holding",
        "metric": f"{insider_pct:.1f}%",
        "target": ">= 40%",
        "status": promoter_status,
        "points": f"{promoter_score}/10",
        "note": promoter_note
    })
    
    # 7. Valuation Discipline (P/E Ratio)
    pe_ratio = info.get("trailingPE", None)
    if pe_ratio is None or pe_ratio <= 0:
        pe_ratio = info.get("forwardPE", 25.0)
    if pe_ratio is None or pe_ratio <= 0:
        pe_ratio = 30.0
        
    pe_score = 0
    if pe_ratio <= 18:
        pe_score = 10
        pe_status = "PASS"
        pe_note = f"Attractive valuation P/E at {pe_ratio:.1f}x"
    elif pe_ratio <= 30:
        pe_score = 8
        pe_status = "PASS"
        pe_note = f"Fair valuation P/E at {pe_ratio:.1f}x"
    elif pe_ratio <= 45:
        pe_score = 4
        pe_status = "WARNING"
        pe_note = f"Rich valuation P/E at {pe_ratio:.1f}x, requires solid growth execution"
    else:
        pe_score = 0
        pe_status = "FAIL"
        pe_note = f"Expensive valuation P/E at {pe_ratio:.1f}x (High multiple risk)"
        
    score += pe_score
    checks.append({
        "category": "Valuation Discipline (P/E)",
        "metric": f"{pe_ratio:.1f}x",
        "target": "< 25-30x",
        "status": pe_status,
        "points": f"{pe_score}/10",
        "note": pe_note
    })
    
    final_percentage = (score / max_score) * 100
    return score, max_score, final_percentage, checks

st.title("🇮🇳 Indian Stock Fundamental Scoring Calculator")
st.markdown("Automate your long-term fundamental analysis checklist for **NSE & BSE** listed companies (inspired by Screener.in metrics). Enter any Indian stock ticker below or select from the preset list to instantly evaluate financial health.")

# Preset Indian Stocks list
preset_stocks = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", 
    "TATAMOTORS", "ITC", "SBIN", "BHARTIARTL", "LICI", 
    "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN", "BAJFINANCE"
]

st.sidebar.header("🔍 Indian Stock Search")
selected_preset = st.sidebar.selectbox("Choose Top Indian Stock or Type Below:", ["-- Select Preset --"] + preset_stocks)

manual_input = st.sidebar.text_input("Or Enter NSE/BSE Ticker Symbol:", value="").strip().upper()

# Determine active ticker
if manual_input:
    ticker_input = manual_input
elif selected_preset != "-- Select Preset --":
    ticker_input = selected_preset
else:
    ticker_input = "RELIANCE"

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 📋 Indian Long-Term Rules:
1. **ROE >= 15%**: High capital compounding.
2. **Debt/Equity < 1.0**: Clean balance sheet.
3. **Interest Coverage > 4x**: Safe debt servicing.
4. **Net Margins >= 10%**: Strong pricing power.
5. **Positive FCF**: Real cash generation.
6. **Promoter Holding >= 40%**: Skin in the game.
7. **Reasonable P/E**: Margin of safety.
""")

analyze_button = st.sidebar.button("Run Fundamental Analysis", type="primary")

if analyze_button or ticker_input:
    with st.spinner(f"Fetching financial data from NSE/BSE and evaluating fundamentals for `{ticker_input}`..."):
        data, error = fetch_indian_stock_data(ticker_input)
        
        if error:
            st.error(f"Error: {error}. Please verify the ticker symbol (e.g., `RELIANCE`, `TCS`, `INFY`).")
        else:
            info = data["info"]
            company_name = info.get("longName", info.get("shortName", ticker_input))
            sector = info.get("sector", "N/A")
            industry = info.get("industry", "N/A")
            market_cap = info.get("marketCap", 0)
            current_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
            currency = info.get("currency", "INR")
            
            # Display Company Header
            st.markdown(f"## {company_name} (`{data['symbol']}`)")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                price_str = f"₹{current_price:,.2f}" if currency == "INR" or current_price > 0 else f"{current_price:,.2f}"
                st.metric("Current Price", price_str)
            with col2:
                if market_cap:
                    mcap_cr = market_cap / 1e7  # Convert to Crores INR roughly
                    market_cap_str = f"₹{mcap_cr:,.2f} Cr" if mcap_cr < 100000 else f"₹{mcap_cr/1e5:,.2f} Lakh Cr"
                else:
                    market_cap_str = "N/A"
                st.metric("Market Cap", market_cap_str)
            with col3:
                st.metric("Sector", sector)
            with col4:
                st.metric("Industry", industry)
            
            st.markdown("---")
            
            # Run Analysis Scorecard
            score, max_score, percentage, checks = analyze_indian_fundamentals(data)
            
            # Overall Score Banner
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
                    verdict = "🟢 **Strong Long-Term Compounder (A-Grade)**: This Indian business exhibits robust capital efficiency, solid promoter backing, and a clean balance sheet matching premier compounding criteria."
                elif percentage >= 50:
                    verdict = "🟡 **Moderate / Mixed Fundamentals (B-Grade)**: The company shows solid strengths in several metrics but has specific areas of vulnerability (such as debt or margins) requiring close scrutiny."
                else:
                    verdict = "🔴 **High Risk / Weak Fundamentals (C-Grade)**: Multiple red flags detected across return ratios, cash generation, or valuations. Exercise extreme caution."
                st.info(verdict)
                
            st.markdown("---")
            
            # Detailed Breakdown Checklist Table
            st.subheader("📋 Granular Checklist Breakdown (Screener-Style)")
            
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
            st.success("Analysis complete! Note: Quantitative screens are your first filter. Always review annual reports, management integrity, and corporate governance before investing in Indian equities.")

else:
    st.info("👈 Choose a stock from the preset dropdown or enter an Indian stock ticker symbol in the sidebar to begin analysis.")
