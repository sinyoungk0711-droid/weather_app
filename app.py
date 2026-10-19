from __future__ import annotations

from datetime import date
from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data" / "weather_app.db"

st.set_page_config(page_title="우리 지역 기후 대시보드", page_icon="🌦️", layout="wide", initial_sidebar_state="expanded")

REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
METRICS = {"평균기온": {"unit": "°C"}, "연강수량": {"unit": "mm"}}
YEARS = list(range(2015, date.today().year))

@st.cache_data
def make_demo_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create synthetic sample values for UI testing, not real observations."""
    normal_rows = []
    annual_rows = []
    for idx, region in enumerate(REGIONS):
        base_temp = 11.2 + (idx % 6) * 0.48 + (0.7 if region in ("부산", "제주", "울산") else 0)
        base_rain = 1050 + (idx * 97) % 520
        normal_rows.append({"지역": region, "평균기온": round(base_temp, 1), "연강수량": int(base_rain)})
        for year in YEARS:
            temp_delta = 0.025 * (year - 2015) + ((idx * 7 + year) % 5 - 2) * 0.08
            rain_delta = ((idx * 19 + year * 13) % 181) - 90
            annual_rows.append({"지역": region, "연도": year, "평균기온": round(base_temp + 0.45 + temp_delta, 1), "연강수량": max(650, int(base_rain + rain_delta))})
    return pd.DataFrame(normal_rows), pd.DataFrame(annual_rows)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS app_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, note TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")


def export_csv(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


normal_df, annual_df = make_demo_data()
init_db()

st.title("🌦️ 우리 지역의 기후는 어떻게 변하고 있을까요?")
st.caption("지역 기후 탐색 시제품 · Python + Streamlit")
st.info("데모 데이터 안내: 현재 표시되는 값은 화면과 기능을 확인하기 위한 예시용 합성 데이터입니다. 실제 기상청 관측값이나 공식 기후 평년값이 아닙니다. 공식 자료 연결 전에는 분석·인용에 사용하지 마세요.", icon="ℹ️")

with st.sidebar:
    st.header("조회 조건")
    selected_regions = st.multiselect("지역 선택", REGIONS, default=["서울", "부산", "강원"], help="한 곳 또는 여러 곳을 선택해 비교할 수 있습니다.")
    metric = st.selectbox("기후 지표", list(METRICS.keys()))
    selected_year = st.selectbox("비교 연도", YEARS, index=len(YEARS) - 1)
    st.divider()
    st.markdown("**데이터 기준**")
    st.caption("평년 기준: 예시용 기준값")
    st.caption(f"비교 연도: {selected_year}년")
    st.caption("자료 상태: 합성 데모 데이터")

if not selected_regions:
    st.warning("비교할 지역을 하나 이상 선택해 주세요.")
    st.stop()

unit = METRICS[metric]["unit"]
recent = annual_df[annual_df["연도"] == selected_year]
comparison = normal_df[normal_df["지역"].isin(selected_regions)].merge(recent[recent["지역"].isin(selected_regions)], on="지역", suffixes=("_평년", "_최근"))
comparison["평년 대비 차이"] = (comparison[f"{metric}_최근"] - comparison[f"{metric}_평년"]).round(1 if unit == "°C" else 0)

st.subheader("한눈에 보는 기후 요약")
primary_region = selected_regions[0]
row = comparison[comparison["지역"] == primary_region].iloc[0]
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(f"{primary_region} · 평년 기준", f"{row[f'{metric}_평년']:,} {unit}")
with col2:
    st.metric(f"{selected_year}년 예시값", f"{row[f'{metric}_최근']:,} {unit}")
with col3:
    delta = row["평년 대비 차이"]
    st.metric("평년 대비 차이", f"{delta:+,.1f} {unit}" if unit == "°C" else f"{delta:+,.0f} {unit}")

st.divider()
left, right = st.columns([1.15, 1])
with left:
    st.subheader("지역별 비교")
    chart_df = comparison[["지역", f"{metric}_평년", f"{metric}_최근"]].melt(id_vars="지역", var_name="구분", value_name=metric)
    chart_df["구분"] = chart_df["구분"].map({f"{metric}_평년": "평년 기준 예시값", f"{metric}_최근": f"{selected_year}년 예시값"})
    fig = px.bar(chart_df, x="지역", y=metric, color="구분", barmode="group", labels={"지역": "지역", metric: f"{metric} ({unit})", "구분": "자료 구분"}, template="plotly_white")
    fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("연도별 예시 추이")
    trend = annual_df[(annual_df["지역"].isin(selected_regions)) & (annual_df["연도"] <= selected_year)]
    trend_fig = px.line(trend, x="연도", y=metric, color="지역", markers=True, labels={"연도": "연도", metric: f"{metric} ({unit})", "지역": "지역"}, template="plotly_white")
    trend_fig.update_layout(legend_title_text="", margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(trend_fig, use_container_width=True)

st.subheader("비교 데이터")
display_df = comparison[["지역", f"{metric}_평년", f"{metric}_최근", "평년 대비 차이"]].copy()
display_df.columns = ["지역", "평년 기준 예시값", f"{selected_year}년 예시값", "평년 대비 차이"]
st.dataframe(display_df, use_container_width=True, hide_index=True)
st.download_button("⬇️ 비교 결과 CSV 다운로드", data=export_csv(display_df), file_name=f"climate_demo_{selected_year}.csv", mime="text/csv")

with st.expander("데이터와 해석에 대한 안내"):
    st.markdown("""
    - 이 화면은 사용자 흐름과 차트 기능을 시험하기 위한 **합성 데이터 데모**입니다.
    - 실제 기후 평년값은 공식 자료의 기준 기간과 집계 방법을 확인해 연결해야 합니다.
    - 관측소 자료를 시·도 대표값으로 바꾸려면 공간 대표성 및 집계 규칙을 별도로 정의해야 합니다.
    - 차이는 선택한 지표에 대해 최근 연도 값에서 평년 기준 값을 뺀 값으로 계산합니다.
    - 다음 단계에서 공식 출처, 자료 기간, 수집 시각, 결측 및 품질 정보를 함께 표시합니다.
    """)
st.caption("시제품 버전 0.1 · 공식 데이터 API는 아직 연결되지 않았습니다.")
