# IDX80 Recovery Scanner

Dashboard Streamlit untuk memindai saham IDX80 dan menampilkan kandidat **recovery**:
saham yang sudah turun dalam, tekanan jual mereda, dan tren mulai berbalik.

![Screenshot](screenshot.png)
<!-- TODO: tambahkan screenshot -->

## Cara kerja
Data harga 1 tahun diambil dari Yahoo Finance (yfinance). Setiap saham diberi skor 0–5
dari lima sinyal:

1. RSI(14) pulih: naik dari oversold (< 30) atau di atas 50
2. MA20 memotong ke atas MA50 dalam 10 hari terakhir
3. Drawdown minimal 20% dari high 1 tahun
4. Volume hari terakhir > rata-rata 50 hari
5. Histogram MACD(12/26/9) positif

Hasil bisa difilter dari sidebar, lalu pilih satu saham untuk melihat chart harga + MA dan RSI.
Jika download gagal (mis. rate limit Yahoo), app memakai data cadangan `snapshot.pkl`.

## Menjalankan
```bash
pip install -r requirements.txt
streamlit run app.py
```

Daftar ticker ada di `idx80.csv` dan perlu diperbarui saat konstituen IDX80 berubah.

## Disclaimer
Ini alat screening, **bukan rekomendasi investasi**. Lakukan analisis sendiri sebelum
mengambil keputusan.
