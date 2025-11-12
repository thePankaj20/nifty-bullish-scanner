import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import os

st.set_page_config(page_title="Bullish Stock Scanner", page_icon="📈", layout="wide", menu_items=None)

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

            cond_ema = last["EMA20"] >= last["EMA50"] * 0.99
            cond_rsi = 50 < last["RSI"] < 70
            cond_price = 98 <= price_position <= 108
            cond_volume = volume_ratio > 0.9

            # Only strong setups
            if cond_ema and cond_rsi and cond_price and cond_volume:
                entry = last["Close"] * 1.005
                target = entry * 1.03
                stoploss = last["EMA20"]
                rr_ratio = (target - entry) / (entry - stoploss) if entry > stoploss else None

                results.append({
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
        except Exception:
            continue

    st.success("✅ Scan completed!")

    if results:
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(by=["Trend_%", "RSI", "VolRatio"], ascending=False)
        df_results = df_results.head(12).reset_index(drop=True)

        st.subheader("📈 Top Bullish Stocks to Consider Buying Tomorrow")
        st.dataframe(df_results, use_container_width=True)

        # Prepare CSV for download
        csv_data = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Download results as CSV",
            data=csv_data,
            file_name="bullish_candidates.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No strong bullish setups found today.")
