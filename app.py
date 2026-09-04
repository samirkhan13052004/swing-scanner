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
st.title("🚀 Institutional Swing Scanner")

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
            st.success("लॉगिन सफल!")
        except Exception as e:
            st.error(f"एरर: {e}")
            st.stop()
            
        stocks = {"RELIANCE":"2885", "TCS":"11536", "INFY":"1594", "HDFCBANK":"1333", "TATASTEEL":"3499", "SBIN":"3045", "ICICIBANK":"4963", "ITC":"1660", "BHARTIARTL":"10604"}
        
        progress_bar = st.progress(0)
        status = st.empty()
        passed = []
        
        for i, (symbol, token) in enumerate(stocks.items()):
            status.text(f"Scanning: {symbol}...")
            df = fetch_data(obj, token, symbol)
            if df is not None:
                is_ok, sl = check_institutional_swing_setup(df)
                if is_ok:
                    passed.append({"Stock": symbol, "Buy Price": f"₹{df['close'].iloc[-1]}", "Stop Loss": f"₹{sl}"})
            time.sleep(0.4)
            progress_bar.progress((i + 1) / len(stocks))
            
        status.text("स्कैन पूरा हुआ!")
        
        if len(passed) > 0:
            st.success("🎯 आज के ट्रेड्स:")
            st.dataframe(pd.DataFrame(passed), use_container_width=True)
        else:
            st.warning("आज कोई ट्रेड नहीं मिला।")
