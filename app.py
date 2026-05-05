import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone
import math

import requests
import uuid

st.write("🔥 TRACKING CODE IS RUNNING")

MEASUREMENT_ID = "G-E49W7H3RQX"
API_SECRET = "Aujz5AJ3QCGLE2Vvijj3fg"

def send_pageview():
    url = f"https://www.google-analytics.com/mp/collect?measurement_id={MEASUREMENT_ID}&api_secret={API_SECRET}"

    payload = {
        "client_id": str(uuid.uuid4()),  # unieke gebruiker
        "events": [
            {
                "name": "page_view",
                "params": {
                    "page_location": "https://signal-scanner.com/",
                    "page_title": "Signal Scanner"
                }
            }
        ]
    }

    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("GA error:", e)

# 👇 BELANGRIJK: dit moet echt runnen bij elke page load
send_pageview()




st.set_page_config(
    page_title="Signal Scanner",
    page_icon="Signal Scanner logo.png"
)


st.set_page_config(
    page_title="Crypto Signal Scanner",
    layout="wide",
    initial_sidebar_state="collapsed"
)



import streamlit as st
import base64

def get_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

img_base64 = get_base64("Signal Scanner logo.png")

st.markdown(f"""
<style>
.rounded-img {{
    width: 150px;
    height: 150px;
    border-radius: 50%;
    object-fit: cover;
}}
</style>

<img src="data:image/png;base64,{img_base64}" class="rounded-img">
""", unsafe_allow_html=True)



st.markdown("""
<style>
button[data-baseweb="tab"] {
    font-size: 20px !important;
    font-weight: 600;
    padding: 10px 18px !important;
}
/* Actual visible text inside tab */
button[data-baseweb="tab"] span {
    font-size: 24px !important;
            
/* Active tab highlight */
button[aria-selected="true"] {
    border-bottom: 4px solid currentColor !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.big-title {
    position: relative;
    top: 0px;
    z-index: 80;
    font-size: 45px;
    font-weight: 800;
    text-align: left;
    
    letter-spacing: 2px;
    margin-bottom: 10px;
}
</style>

<div class="big-title">Crypto Signal Scanner</div>
""", unsafe_allow_html=True)

# =========================
# CONFIG
# =========================
TOP_COINS = {
    "BTC": "XBTUSD",
    "ETH": "ETHUSD",
    "SOL": "SOLUSD",
    "XRP": "XRPUSD",
    "ADA": "ADAUSD",
    "DOT": "DOTUSD",
    "LINK": "LINKUSD",
    "AVAX": "AVAXUSD",
    "DOGE": "DOGEUSD"
}

INTERVAL_MAP = {"1h": 60, "4h": 240, "1d": 1440}

# =========================
# DATA
# =========================
@st.cache_data(ttl=200)
def get_data(symbol, interval):
    url = "https://api.kraken.com/0/public/OHLC"

    r = requests.get(url, params={
        "pair": symbol,
        "interval": INTERVAL_MAP[interval]
    })

    data = r.json()

    if data.get("error"):
        st.error(data["error"])
        return pd.DataFrame()

    pair = list(data["result"].keys())[0]

    df = pd.DataFrame(data["result"][pair], columns=[
        "timestamp","open","high","low","close","vwap","volume","count"
    ])

    df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)

    df = df[["date","open","high","low","close","volume"]]

    for c in ["open","high","low","close","volume"]:
        df[c] = df[c].astype(float)

    return df.tail(566)

# =========================
# INDICATORS
# =========================
def indicators(df):
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()

    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    mid = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std()

    df["bb_upper"] = mid + 2 * std
    df["bb_lower"] = mid - 2 * std

    d = df["close"].diff()
    g = d.clip(lower=0)

    l = -d.clip(upper=0)
    rs = g.ewm(alpha=1/14).mean() / l.ewm(alpha=1/14).mean()
    df["rsi"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df.tail(365)

# LAYER 2: INDICATORS CACHE
# =========================
@st.cache_data(ttl=200)
def compute_indicators(df):
    df = df.copy()

    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()

    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    mid = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std()

    df["bb_upper"] = mid + 2 * std
    df["bb_lower"] = mid - 2 * std

    d = df["close"].diff()
    g = d.clip(lower=0)
    l = -d.clip(upper=0)
    rs = g.ewm(alpha=1/14).mean() / l.ewm(alpha=1/14).mean()
    df["rsi"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
     # ✅ ADD THIS (MISSING BEFORE)
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df

# =========================
# Signals
def add_signal_columns(df):
    df = df.copy()

    prev_close = df["close"].shift(1)
    prev_sma50 = df["sma50"].shift(1)
    prev_sma200 = df["sma200"].shift(1)
    prev_macd = df["macd"].shift(1)
    prev_macd_signal = df["macd_signal"].shift(1)
    prev_rsi = df["rsi"].shift(1)
    prev_bb_upper = df["bb_upper"].shift(1)
    prev_bb_lower = df["bb_lower"].shift(1)

    def check(cond):
        return cond.map({True: "✔", False: ""})

    # Signals
    df["SMA50 ↑"] = check((df["close"] > df["sma50"]) & (prev_close <= prev_sma50))
    df["SMA50 ↓"] = check((df["close"] < df["sma50"]) & (prev_close >= prev_sma50))

    df["Golden Cross"] = check((df["sma50"] > df["sma200"]) & (prev_sma50 <= prev_sma200))
    df["Death Cross"] = check((df["sma50"] < df["sma200"]) & (prev_sma50 >= prev_sma200))

    df["MACD ↑"] = check((df["macd"] > df["macd_signal"]) & (prev_macd <= prev_macd_signal))
    df["MACD ↓"] = check((df["macd"] < df["macd_signal"]) & (prev_macd >= prev_macd_signal))

    df["RSI OB"] = check((df["rsi"] > 70) & (prev_rsi <= 70))
    df["RSI OS"] = check((df["rsi"] < 30) & (prev_rsi >= 30))

    df["BB Break ↑"] = check((prev_close <= prev_bb_upper) & (df["close"] > df["bb_upper"]))
    df["BB Break ↓"] = check((prev_close >= prev_bb_lower) & (df["close"] < df["bb_lower"]))

    return df
# PLOT
# =========================
def plot(df, coin,
         sma50_on, sma200_on,
         ema50_on, ema200_on,
         bb_on, macd_on, rsi_on,
         macd_hist_on):

    rows = 1 + int(macd_on) + int(rsi_on)

    row_heights = [0.6]
    if macd_on:
        row_heights.append(0.35)
    if rsi_on:
        row_heights.append(0.2)

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=row_heights
    )

    price_row = 1
    macd_row = 2 if macd_on else None
    rsi_row = 3 if (macd_on and rsi_on) else (2 if rsi_on else None)

    # =========================
    # PRICE
    # =========================
    fig.add_trace(go.Candlestick(
    x=df["date"],
    close=df["close"],
    high=df["high"],
    open=df["open"],
    low=df["low"],
    name="",
    customdata=df["close"],

    increasing=dict(line=dict(color="#26A69A"), fillcolor="#26A69A"),
    decreasing=dict(line=dict(color="#EF5350"), fillcolor="#EF5350"),
),  row=price_row, col=1)

    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["close"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        name="Close"
    ), row=price_row, col=1)

    fig.update_layout(
        hoverlabel=dict(
        bgcolor="rgba(30,30,30,0.95)",
        font_color="black",
        bordercolor="rgba(255,255,255,0.2)",
        font_size=36
    )
)
    last_price = df["close"].iloc[-1]
    last_open = df["open"].iloc[-1]

    price_color ="#26a66c" if last_price >= last_open else "#e7211e"
    fig.add_hline(
     y=last_price,
     line_dash="dot",
     line_width=1,
     line_color=price_color,
     row=price_row,
     col=1
)

    fig.add_annotation(
     x=1,  # slightly outside chart
     xref="paper",
     y=last_price,
      yref=f"y{price_row}",
     text=f"{last_price}",
     showarrow=False,
     font=dict(color="white"),
     bgcolor=price_color,
     bordercolor="black"
)

    fig.update_yaxes(
    title_text="<b>USD($)<b>",
    title_font=dict(size=18),
    separatethousands=False,
    row=price_row,
    col=1
)
 #Indicators
    if sma50_on:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["sma50"],
            name="SMA 50",
            hoverinfo="skip"
        ), row=price_row, col=1)

    if sma200_on:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["sma200"],
            name="SMA 200",
            hoverinfo="skip"
        ), row=price_row, col=1)

    if ema50_on:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["ema50"],
            name="EMA 50",
            hoverinfo="skip"
        ), row=price_row, col=1)

    if ema200_on:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["ema200"],
            name="EMA 200",
            hoverinfo="skip"
        ), row=price_row, col=1)

    if bb_on:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["bb_upper"],
            name="BB",
            hoverinfo="skip",
            line=dict(color="gray", width=1)
        ), row=price_row, col=1)

        fig.add_trace(go.Scatter(
            x=df["date"], y=df["bb_lower"],
            name="BB Lower",
            hoverinfo="skip",
            line=dict(color="gray", width=1),
            fill="tonexty",
            fillcolor="rgba(128,128,128,0.15)",
            showlegend=False
        ), row=price_row, col=1)

   
 # LIVE PRICE
   


    
    # =========================
    # MACD
    # =========================
    if macd_on:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["macd"],
            line_color="blue", name="MACD"
        ), row=macd_row, col=1)

        fig.add_trace(go.Scatter(
            x=df["date"], y=df["macd_signal"],
            line_color="orange", name="Signal"
        ), row=macd_row, col=1)

        if macd_hist_on:
            colors = ["green" if v >= 0 else "red" for v in df["macd_hist"]]
            fig.add_trace(go.Bar(
                x=df["date"], y=df["macd_hist"],
                marker_color=colors,
                name="Histogram"
            ), row=macd_row, col=1)
        macd_last = df["macd"].iloc[-1]
        signal_last = df["macd_signal"].iloc[-1]

        fig.add_hline(
        y=macd_last,
        line_dash="dot",
        line_color="blue",
        annotation_text=f"{macd_last:.5f}",
        annotation_font_color="white",
        annotation_bgcolor="blue",
        row=macd_row,
        col=1
)

        fig.add_hline(
        y=signal_last,
        line_dash="dot",
        line_color="orange",
        annotation_text=f"{signal_last:.5f}",
        annotation_font_color="white",
        annotation_bgcolor="orange",
        row=macd_row,
        col=1
)
        fig.update_yaxes(
            title_text="<b>MACD<b>",
           title_font=dict(size=18),
          tickformat=".2f",
          separatethousands=False,
          row=macd_row,
          col=1
)
    # =========================
    # RSI
    # =========================
    if rsi_on:
        rsi_last = df["rsi"].iloc[-1]
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["rsi"],
            line_color="purple", name="RSI"
        ), row=rsi_row, col=1)

        fig.add_hline(y=70, line_dash="dash", line_color="white", row=rsi_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="white", row=rsi_row, col=1)

        fig.add_hline(
        y=rsi_last,
        line_dash="dot",
        line_color="purple",
        annotation_text=f"{rsi_last:.2f}",
        annotation_font_color="white",
        annotation_bgcolor="purple",
        row=rsi_row,
        col=1)       
        
        fig.update_yaxes(
          title_text="<b>RSI<b>",
           title_font=dict(size=18),
          tickformat=".2f",
          separatethousands=False,
          row=rsi_row,
          col=1
)

        
    # =========================
    # CROSSHAIR (KEY FEATURE)
    # =========================
    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="white",
        spikethickness=0.5
    )

    fig.update_yaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="white",
        spikethickness=0.5
    )

    # =========================
    # HOVER STYLE
    # =========================
    fig.update_layout(
        hovermode="closest",
        hoverlabel=dict(
            font_color="white",
            bordercolor="rgba(0,0,0,0.2)",
            font_size=12
        )
    )

    # =========================
    # THEME (YOUR ORIGINAL LOOK)
    # =========================
    fig.update_layout(
        plot_bgcolor="#2a2e39"
        
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.10)"
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.10)"
    )

    # =========================
    # FINAL LAYOUT
    # =========================
    fig.update_layout(
    title=dict(
        text=f"<b>{coin} Chart<b>",
        x=0.5,
        xanchor="center",
        font=dict(size=32)
    ),
     height=850,
     dragmode="pan",
     xaxis_rangeslider_visible=False,
     legend=dict(
        orientation="h",
        y=1.01,
        x=0.5,
        xanchor="center"
    )
)

    st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"]
    }
)

#TABS
tab1, tab2, tab3 = st.tabs(["**Crypto Dashboard**", "**Signal Guide**", "**About the Crypto Signal Scanner**"])

# =========================
# UI (STREAMLIT REPLACEMENT)
# =========================
with tab1: 
 st.title("**Crypto Trading Dashboard** 📊")

 coin = st.selectbox("Coin", list(TOP_COINS.keys()))
 tf = st.selectbox("Timeframe", ["1h", "4h", "1d"])

 st.markdown("### Indicators")

 col1, col2 = st.columns(2)

 with col1:
    sma50_on = st.checkbox("SMA 50")
    sma200_on = st.checkbox("SMA 200")
    ema50_on = st.checkbox("EMA 50")
    ema200_on = st.checkbox("EMA 200")

 with col2:
    bb_on = st.checkbox("Bollinger Bands")
    macd_on = st.checkbox("MACD")
    macd_hist_on = st.checkbox("MACD Histogram")
    rsi_on = st.checkbox("RSI")
 refresh = st.button("🔄 Refresh")

 st.caption(f"Last update: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")

# =========================
# RUN
# =========================
 df = get_data(TOP_COINS[coin], tf)

 if not df.empty:
    df = compute_indicators(df)
 
    plot(df, coin,
         sma50_on, sma200_on,
         ema50_on, ema200_on,
         bb_on, macd_on, rsi_on,
         macd_hist_on)
#TOP COINS
 
# TOP SIGNALS ENGINE
# =========================
 st.markdown("---")

 st.markdown("## **Top Setups (Across ALL Timeframes: 1h, 4h, 1d)**")

 from concurrent.futures import ThreadPoolExecutor

# =========================
# PROCESS FUNCTION
# =========================
 def process_coin_multi_tf(item):
    coin, symbol = item
    timeframes = ["1h", "4h", "1d"]

    total_score = 0
    bullish_count = 0
    bearish_count = 0

    for tf in timeframes:
        df = get_data(symbol, tf)

        if df.empty or len(df) < 2:
            continue

        df = compute_indicators(df)

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        signals = []

        # =========================
        # SMA
        # =========================
        signals += [
            1 if (curr["close"] > curr["sma50"] and prev["close"] <= prev["sma50"]) else 0,
            -1 if (curr["close"] < curr["sma50"] and prev["close"] >= prev["sma50"]) else 0,

            1 if (curr["close"] > curr["sma200"] and prev["close"] <= prev["sma200"]) else 0,
            -1 if (curr["close"] < curr["sma200"] and prev["close"] >= prev["sma200"]) else 0,

            1 if (curr["sma50"] > curr["sma200"] and prev["sma50"] <= prev["sma200"]) else 0,
            -1 if (curr["sma50"] < curr["sma200"] and prev["sma50"] >= prev["sma200"]) else 0,
        ]

        # =========================
        # EMA
        # =========================
        signals += [
            1 if (curr["close"] > curr["ema50"] and prev["close"] <= prev["ema50"]) else 0,
            -1 if (curr["close"] < curr["ema50"] and prev["close"] >= prev["ema50"]) else 0,

            1 if (curr["close"] > curr["ema200"] and prev["close"] <= prev["ema200"]) else 0,
            -1 if (curr["close"] < curr["ema200"] and prev["close"] >= prev["ema200"]) else 0,

            1 if (curr["ema50"] > curr["ema200"] and prev["ema50"] <= prev["ema200"]) else 0,
            -1 if (curr["ema50"] < curr["ema200"] and prev["ema50"] >= prev["ema200"]) else 0,
        ]

        # =========================
        # MACD
        # =========================
        signals += [
            1 if (curr["macd"] > curr["macd_signal"] and prev["macd"] <= prev["macd_signal"]) else 0,
            -1 if (curr["macd"] < curr["macd_signal"] and prev["macd"] >= prev["macd_signal"]) else 0,
        ]

        # =========================
        # RSI
        # =========================
        signals += [
            -1 if (curr["rsi"] > 70 and prev["rsi"] <= 70) else 0,  # overbought
            1 if (curr["rsi"] < 30 and prev["rsi"] >= 30) else 0,   # oversold
        ]

        # =========================
        # BOLLINGER
        # =========================
        signals += [
            -1 if (prev["close"] <= prev["bb_upper"] and curr["close"] > curr["bb_upper"]) else 0,
            1 if (prev["close"] >= prev["bb_lower"] and curr["close"] < curr["bb_lower"]) else 0,
        ]

        # =========================
        # AGGREGATE
        # =========================
        total_score += sum(signals)
        bullish_count += sum(1 for s in signals if s == 1)
        bearish_count += sum(1 for s in signals if s == -1)

    return {
        "Coin": coin,
        "Score": total_score,
        "Bullish": bullish_count,
        "Bearish": bearish_count
    }

#BUTTON
# =========================
 if st.button("**Find Top Signal Coins**"):

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_coin_multi_tf, TOP_COINS.items()))

    rank_df = pd.DataFrame(results)

    # =========================
    # TOP BULLISH
    # =========================
    st.markdown("### Top 3 Bullish")

    bull_df = rank_df.sort_values("Score", ascending=False).head(3)

    for _, row in bull_df.iterrows():

     score = row["Score"]

     if score > 0:
        score_color = "green"
     elif score < 0:
        score_color = "red"
     else:
        score_color = "inherit"
     

     st.markdown(
        f"""
        <span style='font-weight:bold'>
            {row['Coin']} → 
            <span style='color:{score_color}'>Score: {score}</span> |
            🟢 <span style='color:green'>{row['Bullish']}</span> /
            🔴 <span style='color:red'>{row['Bearish']}</span>
        </span>
        """,
        unsafe_allow_html=True
     )

    # =========================
    # TOP BEARISH
    # =========================
    st.markdown("### Top 3 Bearish")

    bear_df = rank_df.sort_values("Score", ascending=True).head(3)

    for _, row in bear_df.iterrows():

     score = row["Score"]

     if score > 0:
        score_color = "green"
     elif score < 0:
        score_color = "red"
     else:
        score_color = "inherit"
    

     st.markdown(
        f"""
        <span style='font-weight:bold'>
            {row['Coin']} → 
            <span style='color:{score_color}'>Score: {score}</span> |
            🔴 <span style='color:red'>{row['Bearish']}</span> /
            🟢 <span style='color:green'>{row['Bullish']}</span>
        </span>
        """,
        unsafe_allow_html=True
     )

#SCANNER
 @st.cache_data(ttl=200)
 def build_scanner():
    results = []

    for coin, symbol in TOP_COINS.items():
        for tf in ["1h", "4h", "1d"]:
            df = get_data(symbol, tf)
            if df.empty:
                continue

            df = compute_indicators(df)
            df = add_signal_columns(df)
            
            last = df.iloc[-1]

            results.append({
                "Coin": coin,
                "TF": tf,
                "Price": last["close"],
                "Score": (
                    (1 if last["SMA50 ↑"] else 0) +
                    (-1 if last["SMA50 ↓"] else 0) +
                    (1 if last["MACD ↑"] else 0) +
                    (-1 if last["MACD ↓"] else 0) +
                    (1 if last["RSI OS"] else 0) +
                    (-1 if last["RSI OB"] else 0)
                )
            })

    return pd.DataFrame(results)

 st.markdown("---")
 st.markdown("## **Find ALL current signals**")
 
 
 scanner_tf = st.selectbox(
    "Timeframe",
    ["1h", "4h", "1d"],
    key="scanner_tf_clean"
 )

 utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

 rows = []

 for coin, symbol in TOP_COINS.items():

    df = get_data(symbol, scanner_tf)

    if df.empty:
        continue

    df = compute_indicators(df)

    curr = df.iloc[-1]
    prev = df.iloc[-2]

    price = curr["close"]
    time_utc = curr["date"].strftime("%Y-%m-%d %H:%M")

    # =========================
    # SMA SIGNALS ONLY
    # =========================
    sma50_cross_up = "🟢 SMA50↑" if (curr["close"] > curr["sma50"]) and (prev["close"] <= prev["sma50"]) else ""
    sma50_cross_down = "🔴 SMA50↓" if (curr["close"] < curr["sma50"]) and (prev["close"] >= prev["sma50"]) else ""

    sma200_cross_up = "🟢 SMA200↑" if (curr["close"] > curr["sma200"]) and (prev["close"] <= prev["sma200"]) else ""
    sma200_cross_down = "🔴 SMA200↓" if (curr["close"] < curr["sma200"]) and (prev["close"] >= prev["sma200"]) else ""

    sma_golden = "✨ SMA Golden" if (curr["sma50"] > curr["sma200"]) and (prev["sma50"] <= prev["sma200"]) else ""
    sma_death = "💀 SMA Death" if (curr["sma50"] < curr["sma200"]) and (prev["sma50"] >= prev["sma200"]) else ""

    # =========================
    # EMA SIGNALS ONLY
    # =========================
    ema50_cross_up = "🟢 EMA50↑" if (curr["close"] > curr["ema50"]) and (prev["close"] <= prev["ema50"]) else ""
    ema50_cross_down = "🔴 EMA50↓" if (curr["close"] < curr["ema50"]) and (prev["close"] >= prev["ema50"]) else ""

    ema200_cross_up = "🟢 EMA200↑" if (curr["close"] > curr["ema200"]) and (prev["close"] <= prev["ema200"]) else ""
    ema200_cross_down = "🔴 EMA200↓" if (curr["close"] < curr["ema200"]) and (prev["close"] >= prev["ema200"]) else ""

    ema_golden = "✨ EMA Golden" if (curr["ema50"] > curr["ema200"]) and (prev["ema50"] <= prev["ema200"]) else ""
    ema_death = "💀 EMA Death" if (curr["ema50"] < curr["ema200"]) and (prev["ema50"] >= prev["ema200"]) else ""

    # =========================
    # MACD
    # =========================
    macd_bull = "🟢 MACD Bull" if (curr["macd"] > curr["macd_signal"]) and (prev["macd"] <= prev["macd_signal"]) else ""
    macd_bear = "🔴 MACD Bear" if (curr["macd"] < curr["macd_signal"]) and (prev["macd"] >= prev["macd_signal"]) else ""

    # =========================
    # RSI
    # =========================
    rsi_ob = "🔴 RSI OB" if (curr["rsi"] > 70) and (prev["rsi"] <= 70) else ""
    rsi_os = "🟢 RSI OS" if (curr["rsi"] < 30) and (prev["rsi"] >= 30) else ""

    # =========================
# BOLLINGER BAND SIGNALS
# =========================
    bb_upper_break = ""
    if (prev["close"] <= prev["bb_upper"]) and (curr["close"] > curr["bb_upper"]):
      bb_upper_break = "⬆️ BB Upper"

    bb_lower_break = ""
    if (prev["close"] >= prev["bb_lower"]) and (curr["close"] < curr["bb_lower"]):
      bb_lower_break = "⬇️ BB Lower"

    # =========================
    # ROW (ONLY SIGNALS)
    # =========================
    rows.append({
        "Coin": coin,
        "Timeframe": scanner_tf,
        

        "SMA50": sma50_cross_up + sma50_cross_down,
        "SMA200": sma200_cross_up + sma200_cross_down,
        "SMA Trend": sma_golden + sma_death,

        "EMA50": ema50_cross_up + ema50_cross_down,
        "EMA200": ema200_cross_up + ema200_cross_down,
        "EMA Trend": ema_golden + ema_death,

        "MACD": macd_bull + macd_bear,
        "RSI": rsi_ob + rsi_os,

        "BB": bb_upper_break + bb_lower_break
    })

 scanner_df = pd.DataFrame(rows)

# =========================
# DISPLAY
# =========================
 st.markdown(f"🕒 UTC: **{utc_now}**")
 
 st.dataframe(
    scanner_df,
    use_container_width=True,
    hide_index=True
)
st.markdown(
    """
    <p style='font-size:13px; font-style:italic; color:gray; text-align:center; margin-top:30px;'>
    Disclaimer: All information provided by Crypto Signal Scanner is for educational and informational purposes only and does not constitute financial advice. Trading cryptocurrencies involves risk and you may lose capital.
    Notice: Crypto Signal Scanner does not calculate live market prices itself. Market data provided by Kraken API. This website is not affiliated with Kraken.
    """,
    unsafe_allow_html=True
)


#
# =========================
#
with tab2:

    st.title("Trading Signal Guide")

    st.markdown("## 🟢 Bullish Signals")
    st.markdown("""
 - 🟢 SMA50↑ → Price crosses above SMA 50 line 
 - 🟢 SMA200↑ → Price crosses above SMA 200 line  
 - ✨ SMA Golden → SMA50 line crosses above SMA200 line
 - 🟢 EMA50↑ → Price crosses above EMA 50 line 
 - 🟢 EMA200↑ → Price crosses above EMA 200 line
 - ✨ EMA Golden → EMA50 line crosses above EMA200 line 
 - 🟢 MACD Bull → MACD crosses above signal line  
 - 🟢 RSI OS → RSI crosses below 30  
 - ⬇️ BB Lower → Price crosses lower Bollinger Band  
 """)

    st.markdown("---")

    st.markdown("## 🔴 Bearish Signals")
    st.markdown("""
 - 🔴 SMA50↓ → Price crosses below SMA 50 line 
 - 🔴 SMA200↓ → Price crosses below SMA 200 line  
 - 💀 SMA Death → SMA50 line crosses below SMA200 line  
 - 🔴 EMA50↓ → Price crosses below EMA 50 line  
 - 🔴 EMA200↓ → Price crosses below EMA 200 line  
 - 💀 EMA Death → EMA50 line crosses below EMA200 line 
 - 🔴 MACD Bear → MACD crosses below signal line  
 - 🔴 RSI OB → RSI crosses above 70  
 - ⬆️ BB Upper → Price crosses upper Bollinger Band  
 """)
  
    
with tab3:

    st.title("About Crypto Signal Scanner")

    st.markdown("""
### What is the Crypto Signal Scanner?

The Crypto Signal Scanner is a lightweight crypto analysis tool designed to give you **fast, clear, and actionable market insights** without unnecessary complexity.

Unlike traditional platforms such as TradingView, which can feel overwhelming with advanced tools and cluttered interfaces, the Crypto Signal Scanner focuses on:

- Quick signal detection  
- Clean, easy-to-read charts  
- Simplified indicators (SMA, EMA, MACD, RSI, Bollinger Bands)  
- Fast multi-timeframe scanning  

---

### Our Goal

To help traders and beginners quickly understand market conditions without spending hours analyzing complex charts.

This tool is built for:

- Beginners learning technical analysis  
- Active traders who need fast confirmation signals  
- Users who prefer simplicity over complexity  

---

### **Disclaimer**

Crypto Signal Scanner is **not financial advice**.

All signals, indicators, and analysis provided by this tool are for **educational and informational purposes only**.

You are solely responsible for any trading decisions you make. Cryptocurrency trading involves significant risk, and you may lose all invested capital.
Notice: the Crypto Signal Scanner does not calculate live market prices itself. All price data is sourced from external providers. Always verify live prices with your broker or exchange before making any trading decisions.   
Market data provided by Kraken API. This website is not affiliated with Kraken.                             
""")    
    


    

