import numpy as np
import pandas as pd
import yfinance as yf

# --- Parameter indikator (jangan ubah tanpa konfirmasi) ---
RSI_PERIOD = 14
MA_FAST, MA_SLOW = 20, 50
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
VOL_AVG = 50

# --- Ambang sinyal skor ---
LOOKBACK = 10          # jendela hari untuk MA cross & RSI oversold
RSI_OVERSOLD = 30
RSI_MID = 50
DRAWDOWN_MIN = -20.0   # % dari high periode
VOL_MIN = 1.0

COLUMNS = ["ticker", "harga", "rsi", "ma_cross", "drawdown_pct", "vol_ratio", "macd_pos", "skor"]


def load_tickers(path="idx80.csv"):
    # baca kode saham, tambah suffix .JK untuk yfinance
    codes = pd.read_csv(path)["ticker"].dropna().str.strip().str.upper()
    return [c + ".JK" for c in codes if c]


def fetch_data(tickers):
    # satu kali download untuk semua ticker
    return yf.download(tickers, period="1y", group_by="ticker", progress=False, auto_adjust=True)


def sma(s, n):
    return s.rolling(n).mean()


def rsi(close, n=RSI_PERIOD):
    # RSI Wilder: smoothing eksponensial alpha = 1/n
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = gain / loss
    return 100 - 100 / (1 + rs)


def macd_hist(close):
    macd = close.ewm(span=MACD_FAST, adjust=False).mean() - close.ewm(span=MACD_SLOW, adjust=False).mean()
    signal = macd.ewm(span=MACD_SIGNAL, adjust=False).mean()
    return macd - signal


def get_df(data, ticker):
    # yfinance: MultiIndex (ticker, field) untuk banyak ticker, kolom biasa untuk satu ticker
    if isinstance(data.columns, pd.MultiIndex):
        if ticker not in data.columns.get_level_values(0):
            return None
        return data[ticker]
    return data


def scan_one(df):
    # return dict sinyal, atau None jika data tidak cukup
    if df is None:
        return None
    df = df.dropna(subset=["Close"])
    if len(df) < MA_SLOW + 1:
        return None

    close, high, vol = df["Close"], df["High"], df["Volume"]
    r = rsi(close)
    ma_f, ma_s = sma(close, MA_FAST), sma(close, MA_SLOW)
    hist = macd_hist(close)

    # RSI pulih: sedang naik, dan (baru keluar dari oversold atau sudah > 50)
    rsi_up = r.iloc[-1] > r.iloc[-2]
    rsi_ok = bool(rsi_up and (r.iloc[-LOOKBACK:].min() < RSI_OVERSOLD or r.iloc[-1] > RSI_MID))

    # MA cross: golden cross MA20/MA50 dalam LOOKBACK hari terakhir
    above = ma_f > ma_s
    cross = above & ~above.shift(1, fill_value=True)
    ma_cross = bool(cross.iloc[-LOOKBACK:].any())

    drawdown = (close.iloc[-1] / high.max() - 1) * 100
    avg_vol = vol.iloc[-VOL_AVG:].mean()
    vol_ratio = vol.iloc[-1] / avg_vol if avg_vol > 0 else np.nan
    macd_pos = bool(hist.iloc[-1] > 0)

    skor = sum([rsi_ok, ma_cross, drawdown <= DRAWDOWN_MIN, vol_ratio > VOL_MIN, macd_pos])
    return {
        "harga": round(float(close.iloc[-1]), 2),
        "rsi": round(float(r.iloc[-1]), 1),
        "ma_cross": ma_cross,
        "drawdown_pct": round(float(drawdown), 1),
        "vol_ratio": round(float(vol_ratio), 2),
        "macd_pos": macd_pos,
        "skor": int(skor),
    }


def run_scan(data, tickers):
    rows = []
    for t in tickers:
        try:
            res = scan_one(get_df(data, t))
        except Exception:
            res = None  # data rusak: jangan crash, tandai tidak tersedia
        row = {"ticker": t.removesuffix(".JK")}
        row.update(res or {})
        rows.append(row)
    out = pd.DataFrame(rows).reindex(columns=COLUMNS)
    return out.sort_values(["skor", "drawdown_pct"], ascending=[False, True], na_position="last").reset_index(drop=True)
