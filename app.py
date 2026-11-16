import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import io

# --- 1. Настройка страницы ---
st.set_page_config(page_title="Мониторинг К-Телеком", layout="wide")

# --- 2. Генерация имитационных данных ---
@st.cache_data
def load_data():
    np.random.seed(42)
    routers = [f"router_{i:02d}" for i in range(1, 11)]
    districts = ["Центр", "Север", "Юг", "Запад"]
    data = []
    for r in routers:
        base_ping = np.random.randint(30, 150)
        for minute in range(30):
            ping = max(10, base_ping + np.random.randint(-20, 50))
            download = np.random.uniform(5, 100)
            loss = np.random.uniform(0, 15)

            status = "OK"
            if ping > 200 or loss >= 10:
                status = "CRITICAL"
            elif ping > 90 or loss >= 3:
                status = "MEDIUM"

            data.append({
                "router_id": r,
                "district": np.random.choice(districts),
                "lat": 56.83 + np.random.uniform(-0.05, 0.05),
                "lon": 60.60 + np.random.uniform(-0.05, 0.05),
                "ping_ms": ping,
                "download_mbps": download,
                "packet_loss": loss,
                "status": status,
                "timestamp": pd.Timestamp("2026-11-16") + pd.Timedelta(minutes=minute)
            })
    return pd.DataFrame(data)

df = load_data()

# --- 3. Боковая панель с фильтрами ---
with st.sidebar:
    st.header("Фильтры")
    selected_district = st.selectbox("Район", ["Все"] + list(df["district"].unique()))
    status_filter = st.multiselect("Статус", ["OK", "MEDIUM", "CRITICAL"], default=["OK", "MEDIUM", "CRITICAL"])

filtered = df.copy()
if selected_district != "Все":
    filtered = filtered[filtered["district"] == selected_district]
filtered = filtered[filtered["status"].isin(status_filter)]

# --- 4. Заголовок и ключевые метрики ---
st.title("Мониторинг качества интернет-соединения")
st.caption(f"Показано {len(filtered)} измерений")

col1, col2, col3 = st.columns(3)
col1.metric("Всего роутеров", filtered["router_id"].nunique())
col2.metric("Средний Ping", f"{filtered['ping_ms'].mean():.1f} мс")
col3.metric("Средняя скорость", f"{filtered['download_mbps'].mean():.1f} Мбит/с")

st.divider()

# --- 5. Карта PyDeck с цветовой индикацией ---
st.subheader("Расположение устройств (цвет = статус)")

latest_map = filtered.sort_values("timestamp").groupby("router_id").tail(1)

COLOR_MAP = {
    "OK": [0, 200, 0, 200],
    "MEDIUM": [255, 165, 0, 200],
    "CRITICAL": [255, 0, 0, 200]
}
latest_map["color"] = latest_map["status"].map(COLOR_MAP)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=latest_map,
    get_position=["lon", "lat"],
    get_color="color",
    get_radius=300,
    pickable=True,
)

view_state = pdk.ViewState(
    latitude=56.83,
    longitude=60.60,
    zoom=11,
    pitch=50,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    map_style=None,
    tooltip={"text": "{router_id}\nСтатус: {status}\nPing: {ping_ms} мс"}
)

st.pydeck_chart(deck, use_container_width=True)

# --- 6. Таблица с последними показателями ---
st.subheader("Текущие показатели по роутерам")
latest_table = filtered.sort_values("timestamp").groupby("router_id").tail(1)
st.dataframe(
    latest_table[["router_id", "district", "status", "ping_ms", "download_mbps", "packet_loss"]],
    hide_index=True,
    use_container_width=True
)

# --- 7. Экспорт в Excel ---
st.divider()
st.subheader("Экспорт данных")

buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    filtered.to_excel(writer, index=False, sheet_name="Мониторинг")
buffer.seek(0)

st.download_button(
    label="📥 Скачать отчёт в Excel",
    data=buffer,
    file_name="k-telecom_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          )
