import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

# -------------------- Streamlit Page Setup --------------------
st.set_page_config(page_title="📈 Bullish Stock Scanner", layout="wide")
st.title("📈 NIFTY 500 Bullish Stock Scanner")
st.caption("Find top bullish stocks from NIFTY 500 anytime, anywhere!")

# -------------------- Load Stock List --------------------
default_csv_path = "nifty500list.csv"

if os.path.exists(default_csv_path):
    st.success("✅ Loaded nifty500list.csv from repo")
    df = pd.read_csv(default_csv_path)
    symbols = [sym + ".NS" for sym in df["Symbol"].tolist()]
else:
    uploaded = st.file_uploader("📂 Upload your NIFTY 500 CSV", type=["csv"])
    if not uploaded:
        st.warning("Please upload nifty500list.csv to start scanning.")
        st.stop()
    df = pd.read_csv(uploaded)
    symbols = [sym + ".NS" for sym in df["Symbol"].tolist()]

st.info(f"📊 Loaded {len(symbols)} symbols from stock list")

# -------------------- Safe Download Function --------------------
@st.cache_data(ttl=3600)
def safe_download(symbol):
    if i < 5:  # show only first 5 stocks for debug
        st.write(f"🧩 {symbol}: downloaded {len(df)} rows")
        if not df.empty:
            st.write(df.tail(2))
    """Download with retry to handle Yahoo throttling."""
    for attempt in range(3):
        try:
            df = yf.download(symbol, period="6mo", interval="1d", progress=False)
            if not df.empty:
                return df
        except Exception:
            time.sleep(1)
    return pd.DataFrame()

# -------------------- Run Button --------------------
if st.button("🚀 Run Bullish Scan"):
    bullish_stocks = []
    progress = st.progress(0)
    total = len(symbols)
    data_ok = 0
    empty_count = 0
    for i, symbol in enumerate(symbols):
        if df.empty:
            empty_count += 1
            continue
        else:
            data_ok += 1
        progress.progress((i + 1) / total)
        time.sleep(0.2)  # avoid throttling

        df = safe_download(symbol)

        if df.empty:
            st.write(f"⚠️ {symbol}: no data from Yahoo")
            continue

        try:
            # Add indicators
            df["EMA20"] = ta.ema(df["Close"], length=20)
            df["EMA50"] = ta.ema(df["Close"], length=50)
            df["RSI"] = ta.rsi(df["Close"], length=14)
            df["AvgVol20"] = df["Volume"].rolling(20).mean()
            df.dropna(inplace=True)

            if df.empty or len(df) < 50:
                st.write(f"⚠️ {symbol}: insufficient valid data ({len(df)} rows)")
                continue

            last = df.iloc[-1]
            last_avg_vol = df["AvgVol20"].iloc[-1]
            volume_ratio = last["Volume"] / last_avg_vol if last_avg_vol else 1
            trend_strength = ((last["EMA20"] - last["EMA50"]) / last["EMA50"]) * 100
            price_position = (last["Close"] / last["EMA20"]) * 100

            # Conditions (same as your working script)
            cond_ema = last["EMA20"] > last["EMA50"]
            cond_rsi = 40 < last["RSI"] < 75
            cond_price = 95 <= price_position <= 110
            cond_volume = volume_ratio > 0.8

            if cond_ema and cond_rsi and cond_price and cond_volume:
                entry = last["Close"] * 1.005
                target = entry * 1.03
                stoploss = last["EMA20"]
                rr_ratio = (target - entry) / (entry - stoploss) if entry > stoploss else None

                bullish_stocks.append({
                    "Symbol": symbol.replace(".NS", ""),
                    "Close": round(last["Close"], 2),
                    "RSI": round(last["RSI"], 1),
                    "EMA20": round(last["EMA20"], 2),
                    "EMA50": round(last["EMA50"], 2),
                    "Trend_%": round(trend_strength, 2),
                    "VolRatio": round(volume_ratio, 2),
                    "Entry": round(entry, 2),
                    "Target": round(target, 2),
                    "StopLoss": round(stoploss, 2),
                    "R/R": round(rr_ratio, 2) if rr_ratio else "-"
                })
        except Exception as e:
            st.write(f"⚠️ Error for {symbol}: {e}")
            continue

    # -------------------- Display Results --------------------
    st.write(f"📉 Empty DataFrames: {empty_count}, ✅ With Data: {data_ok}")
    st.success("✅ Scan completed!")

    if bullish_stocks:
        df_results = pd.DataFrame(bullish_stocks)
        df_results = df_results.sort_values(by=["Trend_%", "RSI", "VolRatio"], ascending=False)
        df_results.reset_index(drop=True, inplace=True)

        st.subheader("📊 Top Bullish Stocks for Tomorrow")
        st.dataframe(df_results, use_container_width=True)

        csv_data = df_results.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Download CSV", csv_data, "bullish_candidates.csv", "text/csv")
    else:
        st.warning("⚠️ No bullish setups found today. Check above logs — likely data empty or throttled.")
