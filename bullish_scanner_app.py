import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import os

st.set_page_config(page_title="Bullish Stock Scanner", page_icon="📈", layout="wide")

st.title("📈 NIFTY 500 Bullish Stock Scanner")
st.caption("Smartly filtered top 10–12 stocks with strongest upside potential for tomorrow’s trade")

# Load stock list automatically from repo or via upload
default_csv_path = "nifty500list.csv"

if os.path.exists(default_csv_path):
    st.success("✅ Loaded NIFTY 500 list from repo (nifty500list.csv)")
    df_symbols = pd.read_csv(default_csv_path)
    symbols = [sym + ".NS" for sym in df_symbols["Symbol"].tolist()]
else:
    uploaded_file = st.file_uploader("📂 Upload your NIFTY 500 CSV file", type=["csv"])
    if uploaded_file:
        df_symbols = pd.read_csv(uploaded_file)
        symbols = [sym + ".NS" for sym in df_symbols["Symbol"].tolist()]
    else:
        st.warning("Please upload `nifty500list.csv` to begin scanning.")
        st.stop()

st.info(f"📊 Loaded {len(symbols)} symbols from stock list")

# Run scan button
if st.button("🚀 Run Bullish Scan"):
    results = []

    progress = st.progress(0)
    for i, symbol in enumerate(symbols):
        progress.progress((i + 1) / len(symbols))

        try:
            df = yf.download(symbol, period="6mo", interval="1d", progress=False, auto_adjust=False)
            if df.empty:
                continue

            df["EMA20"] = ta.ema(df["Close"], length=20)
            df["EMA50"] = ta.ema(df["Close"], length=50)
            df["RSI"] = ta.rsi(df["Close"], length=14)
            df["AvgVol20"] = df["Volume"].rolling(20).mean()
            df.dropna(inplace=True)

            last = df.iloc[-1]
            last_avg_vol = df["AvgVol20"].iloc[-1]
            volume_ratio = last["Volume"] / last_avg_vol if last_avg_vol else 1
            trend_strength = ((last["EMA20"] - last["EMA50"]) / last["EMA50"]) * 100
            price_position = (last["Close"] / last["EMA20"]) * 100

            # Scoring system
            score = 0
            if last["EMA20"] > last["EMA50"]:
                score += 2
            elif last["EMA20"] >= last["EMA50"] * 0.99:
                score += 1

            if 55 <= last["RSI"] <= 65:
                score += 1
            elif last["RSI"] > 65:
                score += 2

            if last["Close"] > last["EMA20"]:
                score += 1
            if volume_ratio > 1.2:
                score += 1

            # Only strong setups
            if score >= 4:
                entry = last["Close"] * 1.005
                target = entry * 1.03
                stoploss = last["EMA20"]
                rr_ratio = (target - entry) / (entry - stoploss) if entry > stoploss else None

                results.append({
