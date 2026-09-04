import streamlit as st
import pandas as pd
import pandas_ta as ta
from SmartApi import SmartConnect
import pyotp
import time
import datetime
import requests

# --- 1. द 7-कंडीशन स्कोरिंग इंजन ---
def check_institutional_swing_setup(stock_df):
    try:
        if len(stock_df) < 200:
            return 0, ["Not Enough Data"], 0
            
        # इंडिकेटर्स कैलकुलेट करें
        stock_df['EMA_50'] = ta.ema(stock_df['close'], length=50)
        stock_df['EMA_200'] = ta.ema(stock_df['close'], length=200)
        stock_df['RSI'] = ta.rsi(stock_df['close'], length=14)
        stock_df['ATR'] = ta.atr(stock_df['high'], stock_df['low'], stock_df['close'], length=14)
        stock_df['Avg_Volume'] = ta.sma(stock_df['volume'], length=20)
        
        last = stock_df.iloc[-1]
        
        # पिछले 7 दिनों का डेटा
        recent_7d_high = stock_df['high'].iloc[-8:-1].max()
        recent_7d_low = stock_df['low'].iloc[-8:-1].min()
        range_7d = recent_7d_high - recent_7d_low
        current_atr = last['ATR']
        
        score = 0
        matched = []
        
        # शर्त 1: शॉर्ट-टर्म ट्रेंड
        if last['close'] > last['EMA_50']:
            score += 1
            matched.append("Price > 50 EMA")
            
        # शर्त 2: लॉन्ग-टर्म ट्रेंड
        if last['EMA_50'] > last['EMA_200']:
            score += 1
            matched.append("50 > 200 EMA")
            
        # शर्त 3: मोमेंटम
        if last['RSI'] > 60:
            score += 1
            matched.append("RSI > 60")
            
        # शर्त 4: वोलैटिलिटी कॉन्ट्रैक्शन (Squeeze)
        if range_7d < (current_atr * 1.5):
            score += 1
            matched.append("VCP Squeeze")
            
        # शर्त 5: वॉल्यूम स्पाइक
        if last['volume'] > (last['Avg_Volume'] * 1.5):
            score += 1
            matched.append("High Volume")
            
        # शर्त 6: प्राइस ब्रेकआउट
        if last['close'] > recent_7d_high:
            score += 1
            matched.append("Breakout")
            
        # शर्त 7: पॉजिटिव कैंडल
        if last['close'] > last['open']:
            score += 1
            matched.append("Green Candle")
            
        sl = round(last['close'] - (2 * current_atr), 2)
        
        return score, matched, sl
    except Exception as e:
        return 0, ["Error in Calc"], 0

# --- 2. API डेटा फेचिंग ---
def fetch_data(obj, token, symbol):
    try:
        to_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        from_date = (datetime.datetime.now() - datetime.timedelta(days=250)).strftime("%Y-%m-%d %H:%M")
        params = {"exchange": "NSE", "symboltoken": str(token), "interval": "ONE_DAY", "fromdate": from_date, "todate": to_date}
        data = obj.getCandleData(params)
        if data['status'] == True and data['data'] is not None:
            df = pd.DataFrame(data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            return df
        return None
    except:
        return None

# --- 3. स्मार्ट टोकन इंजन ---
@st.cache_data(ttl=86400)
def get_angel_tokens():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    res = requests.get(url)
    data = res.json()
    token_map = {}
    for item in data:
        if item['exch_seg'] == 'NSE' and '-EQ' in item['symbol']:
            base_symbol = item['symbol'].split('-EQ')[0]
            token_map[base_symbol] = item['token']
    return token_map

# --- 4. प्रीमियम वेबसाइट UI ---
st.set_page_config(page_title="Pro Swing Scanner", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .big-font {font-size:30px !important; font-weight: bold; color: #1E88E5;}
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="big-font">🚀 Nifty 200 Advanced Swing Scanner</p>', unsafe_allow_html=True)
st.markdown("**AI-Powered Scoring Engine:** यह सिस्टम हर शेयर को 7 तकनीकी पैमानों पर मापता है और रैंक करता है।")

st.sidebar.header("🔑 Login Details")
api_key = st.sidebar.text_input("API Key", type="password")
client_id = st.sidebar.text_input("Client ID")
pin = st.sidebar.text_input("Angel One PIN", type="password")
totp_secret = st.sidebar.text_input("TOTP Secret", type="password")

if st.sidebar.button("Start Live Scan ⚡", use_container_width=True):
    if not api_key or not client_id or not pin or not totp_secret:
        st.sidebar.error("सभी डिटेल्स भरें!")
    else:
        try:
            totp = pyotp.TOTP(totp_secret.replace(" ", "")).now()
            obj = SmartConnect(api_key=api_key)
            login_data = obj.generateSession(client_id, pin, totp)
            if login_data['status'] == False:
                st.sidebar.error("लॉगिन फेल!")
                st.stop()
            st.sidebar.success("✅ लॉगिन सफल!")
            
            token_map = get_angel_tokens()
        except Exception as e:
            st.sidebar.error(f"एरर: {e}")
            st.stop()
            
        nifty_200 = [
            "ABB", "ACC", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "ATGL", 
            "AMBUJACEM", "APOLLOHOSP", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "AUROPHARMA", "AXISBANK", 
            "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BAJAJHLDNG", "BALKRISIND", "BANDHANBNK", 
            "BANKBARODA", "BANKINDIA", "MAHABANK", "BATAINDIA", "BEL", "BHARATFORG", "BHEL", "BPCL", 
            "BHARTIARTL", "BOSCHLTD", "BRITANNIA", "CGPOWER", "CANBK", "CHOLAFIN", "CIPLA", "COALINDIA", 
            "COFORGE", "COLPAL", "CONCOR", "CROMPTON", "CUMMINSIND", "DLF", "DABUR", "DIVISLAB", "DIXON", 
            "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "FACT", "FORTIS", "GAIL", 
            "GMRINFRA", "GLENMARK", "GODREJCP", "GODREJPROP", "GRASIM", "GUJGASLTD", "HCLTECH", 
            "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HAVELLS", "HEROMOTOCO", "HINDALCO", "HAL", "HINDCOPPER", 
            "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDBI", "IDFCFIRSTB", "ITC", 
            "INDIANB", "INDHOTEL", "IOC", "IRCTC", "IRFC", "INDIGOPNTS", "IGL", "INDUSINDBK", "NAUKRI", 
            "INFY", "INDIGO", "JSWENERGY", "JSWSTEEL", "JINDALSTEL", "JIOFIN", "JUBLFOOD", "KALYANKJIL", 
            "KOTAKBANK", "L&TFH", "LTTS", "LICHSGFIN", "LTIM", "LT", "LUPIN", "MRF", "M&M", "M&MFIN", 
            "MARICO", "MARUTI", "MAXHEALTH", "MAZDOCK", "METROPOLIS", "MUTHOOTFIN", "NYKAA", "NMDC", 
            "NTPC", "NATIONALUM", "NAVINFLUOR", "NESTLEIND", "OBEROIRLTY", "ONGC", "OIL", "PAYTM", 
            "PIIND", "PIDILITIND", "PEL", "POLYCAB", "PFC", "POWERGRID", "PRESTIGE", "PNB", "RECLTD", 
            "RELIANCE", "RVNL", "MOTHERSON", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SBICARD", 
            "SBILIFE", "SBIN", "SAIL", "SUNPHARMA", "SUNTV", "SUPREMEIND", "SUZLON", "TATACHEM", 
            "TATACOMM", "TCS", "TATACONSUM", "TATAELXSI", "TATAMOTORS", "TATAPOWER", "TATASTEEL", 
            "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UNIONBANK", 
            "UPL", "VBL", "VEDL", "VOLTAS", "WIPRO", "ZEE", "ZOMATO", "ZYDUSLIFE"
        ]
        
        st.markdown("---")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_results = []
        total_stocks = len(nifty_200)
        
        for i, symbol in enumerate(nifty_200):
            status_text.text(f"🔍 Scanning ({i+1}/{total_stocks}): {symbol}...")
            
            token = token_map.get(symbol)
            if token:
                df = fetch_data(obj, token, symbol)
                if df is not None:
                    score, matched_conditions, sl = check_institutional_swing_setup(df)
                    
                    all_results.append({
                        "Stock": symbol,
                        "Raw_Score": score,
                        "Score": f"{score}/7",
                        "LTP (₹)": round(df['close'].iloc[-1], 2),
                        "Stop Loss (₹)": sl if score > 0 else "-",
                        "Matched Conditions": ", ".join(matched_conditions) if score > 0 else "None"
                    })
            
            time.sleep(0.4)
            progress_bar.progress((i + 1) / total_stocks)
            
        status_text.empty()
        progress_bar.empty()
        
        if len(all_results) > 0:
            res_df = pd.DataFrame(all_results)
            res_df = res_df.sort_values(by="Raw_Score", ascending=False).reset_index(drop=True)
            
            res_df.loc[res_df['Raw_Score'] == 7, 'Score'] = '🔥 7/7'
            res_df.loc[res_df['Raw_Score'] == 6, 'Score'] = '⭐ 6/7'
            res_df.loc[res_df['Raw_Score'] == 5, 'Score'] = '👍 5/7'
            
            tab1, tab2, tab3 = st.tabs(["🎯 Perfect Setups (7/7)", "⭐ Potential Watchlist (5 & 6)", "📊 Full Master Log"])
            
            with tab1:
                st.subheader("🔥 100% Institutional Match")
                perfect_df = res_df[res_df['Raw_Score'] == 7].drop(columns=['Raw_Score'])
                if len(perfect_df) > 0:
                    st.dataframe(perfect_df, use_container_width=True, hide_index=True)
                else:
                    st.info("आज किसी भी शेयर ने 7/7 स्कोर नहीं किया।")
                    
            with tab2:
                st.subheader("⭐ Upcoming Breakouts (स्कोर 5 और 6)")
                st.markdown("इन शेयरों को वॉचलिस्ट में रखें। ये कल या परसों ब्रेकआउट दे सकते हैं।")
                potential_df = res_df[(res_df['Raw_Score'] == 5) | (res_df['Raw_Score'] == 6)].drop(columns=['Raw_Score'])
                if len(potential_df) > 0:
                    st.dataframe(potential_df, use_container_width=True, hide_index=True)
                else:
                    st.info("कोई पोटेंशियल ट्रेड नहीं मिला।")
                    
            with tab3:
                st.subheader("📊 Nifty 200 Complete Log")
                st.markdown("यहाँ देखें कि कौन सा शेयर किस वजह से फेल हुआ।")
                full_df = res_df.drop(columns=['Raw_Score'])
                st.dataframe(full_df, use_container_width=True, hide_index=True)
        else:
            st.error("⚠️ कोई डेटा नहीं मिला! यह एंजेल वन API लिमिट या मार्केट डेटा उपलब्ध न होने की वजह से हो सकता है।")
