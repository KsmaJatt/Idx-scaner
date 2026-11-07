from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from scanner import MA_FAST, MA_SLOW, RSI_MID, RSI_OVERSOLD, fetch_data, get_df, load_tickers, rsi, run_scan, sma

SNAPSHOT = Path(__file__).parent / "snapshot.pkl"


@st.cache_data(ttl=3600)
def load_data(tickers):
    # coba live dulu; kalau gagal/kosong, pakai snapshot
    try:
        data = fetch_data(tickers)
        if not data.dropna(how="all").empty:
            data.to_pickle(SNAPSHOT)  # simpan cadangan terbaru
            return data, "live", datetime.now().strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    if SNAPSHOT.exists():
        data = pd.read_pickle(SNAPSHOT)
        return data, "snapshot", str(data.index[-1].date())
    return None, "gagal", ""


st.set_page_config(page_title="IDX80 Recovery Scanner", layout="wide")
st.title("IDX80 Recovery Scanner")

# --- Sidebar ---
sb = st.sidebar
run = sb.button("Run scan", type="primary")
sb.header("Filter")
rsi_max = sb.slider("RSI maksimum", 0, 100, 100)
dd_min = sb.slider("Drawdown minimal (%)", 0, 80, 0, help="Contoh 20 = harga minimal turun 20% dari high 1 tahun")
f_ma = sb.checkbox("MA cross")
f_vol = sb.checkbox("Volume > 1x")
f_macd = sb.checkbox("MACD > 0")

if run:
    # scan hanya saat tombol diklik; hasil disimpan agar filter tidak memicu scan ulang
    tickers = load_tickers(Path(__file__).parent / "idx80.csv")
    with st.spinner("Mengambil data IDX80..."):
        data, source, updated = load_data(tickers)
        result = run_scan(data, tickers) if data is not None else None
    st.session_state.scan = (data, source, updated, result)

if "scan" not in st.session_state:
    st.info("Klik **Run scan** di sidebar untuk mulai.")
else:
    data, source, updated, result = st.session_state.scan
    if data is None:
        st.error("Data tidak bisa diambil dan snapshot belum ada. Coba lagi nanti.")
    else:
        if source == "live":
            st.caption(f"Sumber data: live (yfinance), diambil {updated}")
        else:
            st.caption(f"Sumber data: snapshot, data per {updated} (download live gagal)")

        missing = result["harga"].isna()
        df = result[~missing]
        # filter diterapkan pada hasil scan yang sudah ada
        mask = (df["rsi"] <= rsi_max) & (df["drawdown_pct"] <= -dd_min)
        if f_ma:
            mask &= df["ma_cross"].astype(bool)  # kolom bisa bertipe object karena ada NaN
        if f_vol:
            mask &= df["vol_ratio"] > 1
        if f_macd:
            mask &= df["macd_pos"].astype(bool)
        filtered = df[mask]

        st.write(f"**{len(filtered)}** dari {len(df)} saham lolos filter")
        st.dataframe(filtered, hide_index=True, width="stretch")
        if missing.any():
            st.caption("Data tidak tersedia: " + ", ".join(result.loc[missing, "ticker"]))

        # --- Chart per saham (pilihan hanya dari hasil filter) ---
        if not filtered.empty:
            pick = st.selectbox("Pilih saham untuk chart", filtered["ticker"])
            close = get_df(data, pick + ".JK")["Close"].dropna()

            st.subheader(f"{pick}: harga + MA{MA_FAST}/MA{MA_SLOW}")
            st.line_chart(pd.DataFrame({
                "Close": close,
                f"MA{MA_FAST}": sma(close, MA_FAST),
                f"MA{MA_SLOW}": sma(close, MA_SLOW),
            }))

            st.subheader(f"{pick}: RSI")
            r = rsi(close)
            st.line_chart(pd.DataFrame({
                "RSI": r,
                f"oversold ({RSI_OVERSOLD})": RSI_OVERSOLD,  # garis acuan
                f"tengah ({RSI_MID})": RSI_MID,
            }, index=r.index))

st.divider()
st.caption("Alat screening, bukan rekomendasi investasi.")
