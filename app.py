import streamlit as st
import pandas as pd
import pandas_ta as ta
from SmartApi import SmartConnect
import pyotp
import time
import datetime
import requests

# --- 1. द 7-कंडीशन स्कैनर ---
def check_institutional_swing_setup(stock_df):
    try:
        if len(stock_df) < 200:
            return False, 0
            
        stock_df['EMA_50'] = ta.ema(stock_df['close'], length=50)
        stock_df['EMA_200'] = ta.ema(stock_df['close'], length=200)
        daily_trend_ok = (stock_df['close'].iloc[-1] > stock_df['EMA_50'].iloc[-1]) and \
                         (stock_df['EMA_50'].iloc[-1] > stock_df['EMA_200'].iloc[-1])
                         
        stock_df['RSI'] = ta.rsi(stock_df['close'], length=14)
        rsi_ok = stock_df['RSI'].iloc[-1] > 60
        
        stock_df['ATR'] = ta.atr(stock_df['high'], stock_df['low'], stock_df['close'], length=14)
        current_atr = stock_df['ATR'].iloc[-1]
        
        recent_7d_high = stock_df['high'].iloc[-8:-1].max()
        recent_7d_low = stock_df['low'].iloc[-8:-1].min()
        range_7d = recent_7d_high - recent_7d_low
        squeeze_ok = range_7d < (current_atr * 1.5)
        
        stock_df['Avg_Volume'] = ta.sma(stock_df['volume'], length=20)
        volume_ok = stock_df['volume'].iloc[-1] > (stock_df['Avg_Volume'].iloc[-1] * 1.5)
        breakout_ok = stock_df['close'].iloc[-1] > recent_7d_high
        
        if daily_trend_ok and rsi_ok and squeeze_ok and volume_ok and breakout_ok:
            sl = stock_df['close'].iloc[-1] - (2 * current_atr)
            return True, round(sl, 2)
        else:
            return False, 0
    except Exception as e:
        return False, 0

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

# --- 3. स्मार्ट टोकन इंजन (दिन में सिर्फ 1 बार डाउनलोड होगा) ---
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

# --- 4. वेबसाइट UI ---
st.set_page_config(page_title="Swing Scanner Pro", layout="wide")
st.title("🚀 Nifty 200 Swing Scanner")
st.markdown("यह स्कैनर निफ्टी 200 के स्टॉक्स को 7-कंडीशन फॉर्मूले पर स्कैन करता है।")

st.sidebar.header("🔑 Login Details")
api_key = st.sidebar.text_input("API Key", type="password")
client_id = st.sidebar.text_input("Client ID")
pin = st.sidebar.text_input("Angel One PIN", type="password")
totp_secret = st.sidebar.text_input("TOTP Secret", type="password")

if st.sidebar.button("Start Live Scan", use_container_width=True):
    if not api_key or not client_id or not pin or not totp_secret:
        st.error("सभी डिटेल्स भरें!")
    else:
        try:
            totp = pyotp.TOTP(totp_secret.replace(" ", "")).now()
            obj = SmartConnect(api_key=api_key)
            login_data = obj.generateSession(client_id, pin, totp)
            if login_data['status'] == False:
                st.error("लॉगिन फेल!")
                st.stop()
            st.success("लॉगिन सफल! डेटाबेस लोड हो रहा है...")
            
            # लेटेस्ट टोकन मैप लोड करें
            token_map = get_angel_tokens()
            
        except Exception as e:
            st.error(f"एरर: {e}")
            st.stop()
            
        # निफ्टी 200 स्टॉक्स की लिस्ट (Symbols)
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
        
        progress_bar = st.progress(0)
        status = st.empty()
        passed = []
        
        total_stocks = len(nifty_200)
        
        for i, symbol in enumerate(nifty_200):
            status.text(f"Scanning ({i+1}/{total_stocks}): {symbol}...")
            
            # टोकन इंजन से सही टोकन निकालें
            token = token_map.get(symbol)
            
            if token:
                df = fetch_data(obj, token, symbol)
                if df is not None:
                    is_ok, sl = check_institutional_swing_setup(df)
                    if is_ok:
                        passed.append({"Stock": symbol, "Buy Price": f"₹{df['close'].iloc[-1]}", "Stop Loss": f"₹{sl}"})
            
            # API को ब्लॉक होने से बचाने के लिए 0.4 सेकंड का ब्रेक (200 स्टॉक्स = 80 सेकंड लगेंगे)
            time.sleep(0.4)
            progress_bar.progress((i + 1) / total_stocks)
            
        status.text("स्कैन पूरा हुआ!")
        
        if len(passed) > 0:
            st.success(f"🎯 शानदार! आज {len(passed)} स्टॉक्स में ट्रेडिंग का मौका है:")
            st.dataframe(pd.DataFrame(passed), use_container_width=True)
        else:
            st.warning("आज किसी भी स्टॉक ने कड़ा इंस्टीट्यूशनल सेटअप पास नहीं किया। मार्केट शांत है।")
