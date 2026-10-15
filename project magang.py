import io
import re
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# 1. KONFIGURASI APLIKASI
# =========================================================

st.set_page_config(
    page_title="Seismo Analytics",
    page_icon="🌏",
    layout="wide"
)

st.title("🌏 Seismo Analytics")
st.subheader("Dashboard Analisis Statistik Gempa Bumi")
st.caption(
    "Prototipe analisis katalog gempa untuk mendukung "
    "pengolahan data BMKG Geofisika."
)


# =========================================================
# 2. DATA CONTOH UNTUK UJI COBA
# Data ini sintetis, bukan data resmi BMKG.
# =========================================================

def buat_data_contoh():
    return pd.DataFrame({
        "datetime": [
            "2026-02-01 02:15:00",
            "2026-02-03 10:20:00",
            "2026-02-03 18:45:00",
            "2026-02-10 07:30:00",
            "2026-02-15 13:10:00"
        ],
        "latitude": [-0.50, -1.20, -0.80, -1.50, -0.70],
        "longitude": [119.80, 120.10, 119.90, 120.30, 119.60],
        "depth_km": [10, 35, 18, 70, 42],
        "magnitude": [3.2, 4.1, 2.8, 5.0, 3.9]
    })


# =========================================================
# 3. MEMBACA DAN MENYERAGAMKAN NAMA KOLOM
# =========================================================

def normalisasi_nama(nama):
    nama = str(nama).strip().lower()
    return re.sub(r"[^a-z0-9]", "", nama)


ALIAS_KOLOM = {
    "datetime": [
        "datetime", "tanggal", "waktu", "origin time",
        "date", "tanggal waktu", "tanggal kejadian",
        "ot", "time"
    ],
    "latitude": [
        "latitude", "lintang", "lat", "garis lintang"
    ],
    "longitude": [
        "longitude", "bujur", "lon", "long",
        "garis bujur"
    ],
    "depth_km": [
        "depth_km", "depth", "kedalaman",
        "kedalaman km", "depth (km)"
    ],
    "magnitude": [
        "magnitude", "magnitudo", "mag",
        "magnitude ml", "mag ml"
    ]
}


def rapikan_kolom(df):
    df = df.copy()

    # Membuat peta nama kolom berdasarkan nama yang dinormalisasi
    peta = {
        normalisasi_nama(kunci): kunci
        for kunci in df.columns
    }

    nama_baru = {}

    for kolom_tujuan, daftar_alias in ALIAS_KOLOM.items():
        for alias in daftar_alias:
            alias_normal = normalisasi_nama(alias)

            if alias_normal in peta:
                nama_asli = peta[alias_normal]
                nama_baru[nama_asli] = kolom_tujuan
                break

    df = df.rename(columns=nama_baru)

    kolom_wajib = [
        "datetime", "latitude", "longitude",
        "depth_km", "magnitude"
    ]

    kolom_hilang = [
        kolom for kolom in kolom_wajib
        if kolom not in df.columns
    ]

    if kolom_hilang:
        raise ValueError(
            "Kolom berikut belum ditemukan: "
            + ", ".join(kolom_hilang)
            + ". Pastikan file memiliki kolom tanggal/waktu, "
            "latitude, longitude, kedalaman, dan magnitudo."
        )

    df = df[kolom_wajib].copy()

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        errors="coerce",
        dayfirst=True
    )

    for kolom in [
        "latitude", "longitude", "depth_km", "magnitude"
    ]:
        df[kolom] = pd.to_numeric(
            df[kolom].astype(str).str.replace(",", ".", regex=False),
            errors="coerce"
        )

    # Menghapus baris dengan nilai yang tidak lengkap
    df = df.dropna(subset=kolom_wajib)

    # Memeriksa koordinat geografis dan nilai yang masuk akal
    df = df[
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
        & (df["depth_km"] >= 0)
        & (df["magnitude"] >= 0)
    ]

    return df.sort_values("datetime").reset_index(drop=True)


# =========================================================
# 4. UNGGAH FILE ATAU GUNAKAN DATA CONTOH
# =========================================================

st.sidebar.header("📂 Sumber Data")

mode_data = st.sidebar.radio(
    "Pilih sumber data",
    ["Unggah CSV/Excel", "Gunakan data contoh"]
)

file_upload = None

if mode_data == "Unggah CSV/Excel":
    file_upload = st.sidebar.file_uploader(
        "Pilih file katalog gempa",
        type=["csv", "xlsx", "xls"]
    )

    st.sidebar.info(
        "File harus memuat waktu, latitude, longitude, "
        "kedalaman, dan magnitudo."
    )
else:
    contoh_csv = buat_data_contoh().to_csv(index=False).encode("utf-8")

    st.sidebar.download_button(
        "Unduh CSV data contoh",
        data=contoh_csv,
        file_name="contoh_data_gempa.csv",
        mime="text/csv"
    )


# =========================================================
# 5. MEMPROSES DATA
# =========================================================

df_asli = None

try:
    if mode_data == "Gunakan data contoh":
        df_asli = rapikan_kolom(buat_data_contoh())

    elif file_upload is not None:
        nama_file = file_upload.name.lower()

        if nama_file.endswith(".csv"):
            try:
                df_baca = pd.read_csv(file_upload, sep=None, engine="python")
            except UnicodeDecodeError:
                file_upload.seek(0)
                df_baca = pd.read_csv(
                    file_upload,
                    sep=None,
                    engine="python",
                    encoding="latin-1"
                )
        else:
            df_baca = pd.read_excel(file_upload)

        df_asli = rapikan_kolom(df_baca)

except Exception as e:
    st.error(f"Gagal membaca data: {e}")


# =========================================================
# 6. DASHBOARD DAN ANALISIS
# =========================================================

if df_asli is None:
    st.info(
        "Silakan unggah file CSV/Excel atau pilih "
        "'Gunakan data contoh' pada menu sebelah kiri."
    )
    st.stop()

if df_asli is None or df_asli.empty:
    st.error(
        "Tidak ada baris data valid. Periksa format tanggal, "
        "koordinat, kedalaman, dan magnitudo."
    )
    st.stop()

st.success(f"Data berhasil dibaca: {len(df_asli)} kejadian valid.")

# -------------------------
# Filter data
# -------------------------

st.sidebar.header("🔎 Filter Analisis")

tanggal_min = df_asli["datetime"].min().date()
tanggal_max = df_asli["datetime"].max().date()

rentang_tanggal = st.sidebar.date_input(
    "Rentang tanggal",
    value=(tanggal_min, tanggal_max),
    min_value=tanggal_min,
    max_value=tanggal_max
)

if isinstance(rentang_tanggal, (tuple, list)):
    if len(rentang_tanggal) == 2:
        tanggal_awal, tanggal_akhir = rentang_tanggal
    else:
        tanggal_awal = rentang_tanggal[0]
        tanggal_akhir = rentang_tanggal[0]
else:
    tanggal_awal = rentang_tanggal
    tanggal_akhir = rentang_tanggal

mag_min = float(df_asli["magnitude"].min())
mag_max = float(df_asli["magnitude"].max())
depth_min = float(df_asli["depth_km"].min())
depth_max = float(df_asli["depth_km"].max())

filter_mag = st.sidebar.slider(
    "Rentang magnitudo",
    min_value=mag_min,
    max_value=mag_max if mag_max > mag_min else mag_min + 0.1,
    value=(mag_min, mag_max),
    step=0.1
)

filter_depth = st.sidebar.slider(
    "Rentang kedalaman (km)",
    min_value=depth_min,
    max_value=depth_max if depth_max > depth_min else depth_min + 1.0,
    value=(depth_min, depth_max),
    step=1.0
)

df = df_asli[
    (df_asli["datetime"].dt.date >= tanggal_awal)
    & (df_asli["datetime"].dt.date <= tanggal_akhir)
    & (df_asli["magnitude"] >= filter_mag[0])
    & (df_asli["magnitude"] <= filter_mag[1])
    & (df_asli["depth_km"] >= filter_depth[0])
    & (df_asli["depth_km"] <= filter_depth[1])
].copy()

if df.empty:
    st.warning("Tidak ada data yang sesuai dengan filter.")
    st.stop()

# -------------------------
# Ringkasan statistik
# -------------------------

st.header("1. Ringkasan Statistik")

c1, c2, c3 = st.columns(3)
c1.metric("Jumlah kejadian", f"{len(df):,}")
c2.metric("Magnitudo rata-rata", f"{df['magnitude'].mean():.2f}")
c3.metric("Magnitudo maksimum", f"{df['magnitude'].max():.2f}")

c4, c5, c6 = st.columns(3)
c4.metric("Median magnitudo", f"{df['magnitude'].median():.2f}")
c5.metric("Kedalaman rata-rata", f"{df['depth_km'].mean():.2f} km")
c6.metric("Kedalaman maksimum", f"{df['depth_km'].max():.2f} km")

# -------------------------
# Tabel statistik
# -------------------------

st.header("2. Tabel Statistik Deskriptif")

statistik = pd.DataFrame({
    "Ukuran Statistik": [
        "Rata-rata", "Median", "Minimum",
        "Maksimum", "Simpangan baku"
    ],
    "Magnitudo": [
        df["magnitude"].mean(),
        df["magnitude"].median(),
        df["magnitude"].min(),
        df["magnitude"].max(),
        df["magnitude"].std()
    ],
    "Kedalaman (km)": [
        df["depth_km"].mean(),
        df["depth_km"].median(),
        df["depth_km"].min(),
        df["depth_km"].max(),
        df["depth_km"].std()
    ]
})

st.dataframe(
    statistik.round(3),
    use_container_width=True,
    hide_index=True
)

# -------------------------
# Histogram
# -------------------------

st.header("3. Grafik Distribusi")

g1, g2 = st.columns(2)

with g1:
    fig_mag = px.histogram(
        df,
        x="magnitude",
        nbins=10,
        title="Histogram Magnitudo",
        labels={"magnitude": "Magnitudo", "count": "Jumlah kejadian"}
    )
    fig_mag.update_layout(
        xaxis_title="Magnitudo",
        yaxis_title="Jumlah kejadian"
    )
    st.plotly_chart(fig_mag, use_container_width=True)

with g2:
    fig_depth = px.histogram(
        df,
        x="depth_km",
        nbins=10,
        title="Histogram Kedalaman",
        labels={"depth_km": "Kedalaman (km)", "count": "Jumlah kejadian"}
    )
    fig_depth.update_layout(
        xaxis_title="Kedalaman (km)",
        yaxis_title="Jumlah kejadian"
    )
    st.plotly_chart(fig_depth, use_container_width=True)

# -------------------------
# Jumlah kejadian terhadap waktu
# -------------------------

st.header("4. Grafik Jumlah Gempa terhadap Waktu")

periode = st.selectbox(
    "Pengelompokan waktu",
    ["Harian", "Mingguan", "Bulanan"]
)

data_waktu = df.set_index("datetime")

if periode == "Harian":
    jumlah_waktu = data_waktu.resample("D").size()
elif periode == "Mingguan":
    jumlah_waktu = data_waktu.resample("W").size()
else:
    jumlah_waktu = data_waktu.resample("MS").size()

jumlah_waktu = jumlah_waktu.reset_index(name="jumlah_gempa")
jumlah_waktu = jumlah_waktu[
    jumlah_waktu["jumlah_gempa"] > 0
]

fig_waktu = px.line(
    jumlah_waktu,
    x="datetime",
    y="jumlah_gempa",
    markers=True,
    title=f"Jumlah Kejadian Gempa per {periode}",
    labels={
        "datetime": "Waktu",
        "jumlah_gempa": "Jumlah kejadian"
    }
)
st.plotly_chart(fig_waktu, use_container_width=True)

# -------------------------
# Scatter plot
# -------------------------

st.header("5. Scatter Plot Magnitudo terhadap Kedalaman")

fig_scatter = px.scatter(
    df,
    x="depth_km",
    y="magnitude",
    hover_data=["datetime", "latitude", "longitude"],
    title="Hubungan Magnitudo dan Kedalaman",
    labels={
        "depth_km": "Kedalaman (km)",
        "magnitude": "Magnitudo"
    }
)
st.plotly_chart(fig_scatter, use_container_width=True)

# -------------------------
# Peta episenter
# -------------------------

st.header("6. Peta Episenter Gempa")

fig_peta = px.scatter_map(
    df,
    lat="latitude",
    lon="longitude",
    color="magnitude",
    size="magnitude",
    hover_name="datetime",
    hover_data={
        "latitude": True,
        "longitude": True,
        "depth_km": True,
        "magnitude": True
    },
    zoom=4,
    height=500,
    title="Sebaran Episenter Gempa"
)
fig_peta.update_layout(map_style="open-street-map")
st.plotly_chart(fig_peta, use_container_width=True)

st.caption(
    "Peta dasar membutuhkan koneksi internet. "
    "Posisi titik mengikuti koordinat pada file."
)

# -------------------------
# Tabel data hasil filter
# -------------------------

st.header("7. Data Gempa yang Dianalisis")

tampilkan = df.rename(columns={
    "datetime": "Tanggal dan Waktu",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "depth_km": "Kedalaman (km)",
    "magnitude": "Magnitudo"
})

st.dataframe(
    tampilkan,
    use_container_width=True,
    hide_index=True
)

# -------------------------
# Ekspor hasil
# -------------------------

st.header("8. Unduh Hasil Analisis")

csv_hasil = tampilkan.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "⬇️ Unduh data hasil (CSV)",
    data=csv_hasil,
    file_name="hasil_analisis_gempa.csv",
    mime="text/csv"
)

buffer_excel = io.BytesIO()

with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
    tampilkan.to_excel(
        writer, sheet_name="Data Gempa", index=False
    )
    statistik.round(3).to_excel(
        writer, sheet_name="Statistik", index=False
    )

st.download_button(
    "⬇️ Unduh laporan data (Excel)",
    data=buffer_excel.getvalue(),
    file_name="hasil_analisis_gempa.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()
st.caption(
    "Seismo Analytics — prototipe akademik. "
    "Periksa kualitas data dan validasi hasil sebelum digunakan "
    "untuk analisis operasional."
)