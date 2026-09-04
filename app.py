import streamlit as st
import pandas as pd
import pandas_ta as ta
from SmartApi import SmartConnect
from loguru import logger
import pyotp
import time
import datetime

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

# --- 3. वेबसाइट UI ---
st.set_page_config(page_title="Swing Scanner Pro", layout="wide")
st.title("🚀 Nifty 50 Swing Scanner")
st.markdown("यह स्कैनर निफ्टी 50 के सभी स्टॉक्स को 7-कंडीशन फॉर्मूले पर लाइव चेक करता है।")

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
            st.success("लॉगिन सफल! स्कैनिंग शुरू हो रही है...")
        except Exception as e:
            st.error(f"एरर: {e}")
            st.stop()
            
        # निफ्टी 50 के सभी स्टॉक्स की डिक्शनरी (Symbol: Token)
        stocks = {
            "ADANIENT": "25", "ADANIPORTS": "15083", "APOLLOHOSP": "157", "ASIANPAINT": "236", 
            "AXISBANK": "5900", "BAJAJ-AUTO": "16669", "BAJFINANCE": "317", "BAJAJFINSV": "16675", 
            "BPCL": "526", "BHARTIARTL": "10604", "BRITANNIA": "547", "CIPLA": "694", 
            "COALINDIA": "20374", "DIVISLAB": "10940", "DRREDDY": "881", "EICHERMOT": "910", 
            "GRASIM": "1232", "HCLTECH": "7229", "HDFCBANK": "1333", "HDFCLIFE": "467", 
            "HEROMOTOCO": "1348", "HINDALCO": "1363", "HINDUNILVR": "1394", "ICICIBANK": "4963", 
            "INDUSINDBK": "5258", "INFY": "1594", "ITC": "1660", "JSWSTEEL": "11723", 
            "KOTAKBANK": "1922", "LTIM": "17818", "LT": "11483", "M&M": "2031", 
            "MARUTI": "10999", "NTPC": "11630", "NESTLEIND": "17963", "ONGC": "2475", 
            "POWERGRID": "14977", "RELIANCE": "2885", "SBILIFE": "21808", "SBIN": "3045", 
            "SHRIRAMFIN": "4306", "SUNPHARMA": "3351", "TCS": "11536", "TATACONSUM": "3432", 
            "TATAMOTORS": "3456", "TATASTEEL": "3499", "TECHM": "13538", "TITAN": "3506", 
            "ULTRACEMCO": "11532", "WIPRO": "3787"
        }
        
        progress_bar = st.progress(0)
        status = st.empty()
        passed = []
        
        for i, (symbol, token) in enumerate(stocks.items()):
            status.text(f"Scanning ({i+1}/50): {symbol}...")
            df = fetch_data(obj, token, symbol)
            if df is not None:
                is_ok, sl = check_institutional_swing_setup(df)
                if is_ok:
                    passed.append({"Stock": symbol, "Buy Price": f"₹{df['close'].iloc[-1]}", "Stop Loss": f"₹{sl}"})
            
            # API को ब्लॉक होने से बचाने के लिए 0.4 सेकंड का ब्रेक
            time.sleep(0.4)
            progress_bar.progress((i + 1) / len(stocks))
            
        status.text("स्कैन पूरा हुआ!")
        
        if len(passed) > 0:
            st.success("🎯 आज के लिए पास हुए स्टॉक्स:")
            st.dataframe(pd.DataFrame(passed), use_container_width=True)
        else:
            st.warning("आज किसी भी स्टॉक ने कड़ा इंस्टीट्यूशनल सेटअप पास नहीं किया। शांति से बैठें!")
