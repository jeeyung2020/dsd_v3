# -*- coding: utf-8 -*-
"""
Streamlit Monthly Sales Dashboard — Brand Themed

사용 방법
1) 아래 패키지 설치 후 실행
   pip install --upgrade streamlit plotly pandas
2) 이 파일을 app.py 로 저장한 뒤 터미널에서 실행
   streamlit run app.py

CSV 헤더 예시: 월, 매출액, 전년동월, 증감률
(영문 헤더도 허용: Month, Sales, LY, YoY)
"""

import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(
    page_title="월별 매출 대시보드 (브랜드 테마)",
    layout="wide",
    page_icon="📈",
)

# ---------------------------
# Brand Colors (Updated)
# ---------------------------
BRAND = {
    "yellow": "#D9DA03",   # Primary accent
    "beige": "#DDCCBB",   # Secondary accent
    "gray": "#6E6665",    # Neutral / text
    "dark": "#231914",    # Dark base
    "orange": "#EC792C",  # Highlight
}

def rgba(hex_color: str, a: float) -> str:
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{a})"

# ---------------------------
# Header (심플한 흰 배경)
# ---------------------------
st.markdown(
    f"""
    <div style="padding:12px 16px;border-radius:14px;background:#FFFFFF;border:1px solid {rgba(BRAND['dark'],0.08)}">
      <h1 style="margin:0;font-size:26px;color:{BRAND['dark']}">📈 월별 매출 대시보드 <span style="font-weight:400;color:{rgba(BRAND['gray'],0.8)}">(브랜드 테마)</span></h1>
      <div style="margin-top:6px;color:{rgba(BRAND['gray'],0.7)}">CSV 업로드 후 5개 시각화가 자동 생성됩니다. (매출 추세, 전년 비교, 증감률, 누적 매출, 최고·최저)</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("데이터 업로드")
    file = st.file_uploader("CSV 파일을 업로드하세요", type=["csv"])  # expects UTF-8
    st.markdown(
        """
        **필수 컬럼**
        - `월` (YYYY-MM)
        - `매출액` (정수)
        - `전년동월` (정수)
        - `증감률` (%, 소수 가능)

        ⚙️ 영문 헤더도 허용: `Month`, `Sales`, `LY`, `YoY`
        """
    )

# ---------------------------
# Helpers
# ---------------------------
KOR_KEYS = {
    "월": ["월", "Month", "month"],
    "매출액": ["매출액", "Sales", "sales"],
    "전년동월": ["전년동월", "LY", "Prev", "prev", "last_year"],
    "증감률": ["증감률", "YoY", "yoy", "chg"],
}


def pick_col(df: pd.DataFrame, keys):
    for k in keys:
        if k in df.columns:
            return k
    return None


@st.cache_data(show_spinner=False)
def load_csv(_file) -> pd.DataFrame:
    df = pd.read_csv(_file)
    return df


@st.cache_data(show_spinner=False)
def normalize_df(df_in: pd.DataFrame) -> pd.DataFrame:
    df = df_in.copy()

    # 공백 제거 및 문자열화
    df.columns = [str(c).strip() for c in df.columns]

    col_month = pick_col(df, KOR_KEYS["월"]) or "월"
    col_sales = pick_col(df, KOR_KEYS["매출액"]) or "매출액"
    col_ly = pick_col(df, KOR_KEYS["전년동월"]) or "전년동월"
    col_yoy = pick_col(df, KOR_KEYS["증감률"]) or "증감률"

    # 누락 컬럼 체크
    missing = [c for c in [col_month, col_sales, col_ly, col_yoy] if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼을 찾을 수 없습니다: {missing}")

    out = pd.DataFrame()
    out["월"] = df[col_month].astype(str).str.strip()

    # 숫자 변환 (숫자/%, 천단위 기호 제거)
    def to_num(s):
        if pd.isna(s):
            return None
        s = str(s)
        s = s.replace('%', '')
        s = ''.join(ch for ch in s if ch.isdigit() or ch in ['-', '.'])
        try:
            return float(s)
        except Exception:
            return None

    out["매출액"] = df[col_sales].map(to_num)
    out["전년동월"] = df[col_ly].map(to_num)
    out["증감률"] = df[col_yoy].map(
        lambda x: float(str(x).replace('%', '')) if pd.notna(x) and str(x).strip() != '' else None)

    # 월 파싱 및 정렬
    out["_dt"] = pd.to_datetime(out["월"], format="%Y-%m", errors="coerce")
    out = out.dropna(subset=["_dt", "매출액"]).copy()
    out = out.sort_values("_dt").reset_index(drop=True)

    # 파생
    out["매출차액"] = (out["매출액"] - out["전년동월"]).fillna(0)
    out["누적매출"] = out["매출액"].cumsum()

    return out

# ---------------------------
# Plotly layout helper with brand theme
# ---------------------------

def apply_brand_layout(fig: go.Figure, title: str, yaxis_title: str | None = None):
    fig.update_layout(
        title= dict(text=title, x=0.01, font=dict(color=BRAND['dark'], size=18)),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor=rgba(BRAND['yellow'], 0.06),
        font=dict(color=BRAND['dark']),
        hovermode="x unified",
        legend=dict(orientation='h', y=-0.2),
        xaxis=dict(showgrid=True, gridcolor=rgba(BRAND['gray'], 0.15), zeroline=False),
        yaxis=dict(title=yaxis_title, showgrid=True, gridcolor=rgba(BRAND['gray'], 0.15), zeroline=True,
                   zerolinecolor=rgba(BRAND['gray'], 0.4)),
        margin=dict(t=60, l=50, r=30, b=60),
    )

# ---------------------------
# Main
# ---------------------------
if not file:
    st.info("좌측 사이드바에서 CSV 파일을 업로드하세요. 예: 2024-01, 12000000, 10500000, 14.3")
    st.stop()

try:
    df_raw = load_csv(file)
    df = normalize_df(df_raw)
except Exception as e:
    st.error(f"데이터 로딩/정규화 중 오류: {e}")
    st.stop()

# KPI 계산
총매출 = float(df["매출액"].sum())
평균매출 = float(df["매출액"].mean()) if len(df) else 0.0
최고_idx = int(df["매출액"].idxmax())
최저_idx = int(df["매출액"].idxmin())
최고월, 최고매출 = df.loc[최고_idx, "월"], float(df.loc[최고_idx, "매출액"])
최저월, 최저매출 = df.loc[최저_idx, "월"], float(df.loc[최저_idx, "매출액"])

# KPI 영역
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("총매출", f"{총매출:,.0f} 원")
with c2:
    st.metric("평균 매출", f"{평균매출:,.0f} 원")
with c3:
    st.metric("최고 매출 월", f"{최고월}", help=f"{최고매출:,.0f} 원")
with c4:
    st.metric("최저 매출 월", f"{최저월}", help=f"{최저매출:,.0f} 원")

# 공통 x축 라벨
labels = df["월"].tolist()
sales = df["매출액"].tolist()
ly = df["전년동월"].tolist() if "전년동월" in df.columns else [None] * len(df)
yoy = df["증감률"].tolist() if "증감률" in df.columns else [None] * len(df)
cum = df["누적매출"].tolist()

# 1) 월별 매출 추세
fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=labels, y=sales, mode="lines+markers", name="당년 매출",
                          line=dict(color=BRAND['orange'], width=3),
                          marker=dict(color=BRAND['orange'], size=6)))
if any(pd.notna(ly)):
    fig1.add_trace(go.Scatter(x=labels, y=ly, mode="lines+markers", name="전년 매출",
                              line=dict(color=BRAND['gray'], width=2, dash="dot"),
                              marker=dict(color=BRAND['gray'], size=5)))
apply_brand_layout(fig1, "월별 매출 추세", "매출액(원)")
st.plotly_chart(fig1, use_container_width=True, theme="streamlit")

# 2) 전년 대비 월별 매출 비교
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=labels, y=sales, name="당년", marker_color=rgba(BRAND['orange'], 0.95)))
if any(pd.notna(ly)):
    fig2.add_trace(go.Bar(x=labels, y=ly, name="전년", marker_color=rgba(BRAND['dark'], 0.9)))
fig2.update_layout(barmode="group")
apply_brand_layout(fig2, "전년 대비 월별 매출 비교", "매출액(원)")
st.plotly_chart(fig2, use_container_width=True, theme="streamlit")

# 3) 전년 대비 증감률
bar_colors = [
    rgba(BRAND['yellow'], 0.9) if (v is not None and v >= 0)
    else rgba(BRAND['dark'], 0.85)
    for v in yoy
]
fig3 = go.Figure(go.Bar(x=labels, y=yoy, marker_color=bar_colors, name="증감률"))
fig3.add_hline(y=0, line_color=rgba(BRAND['gray'], 0.5))
apply_brand_layout(fig3, "전년 대비 증감률", "증감률(%)")
st.plotly_chart(fig3, use_container_width=True, theme="streamlit")

# 4) 누적 매출
fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=labels, y=cum, mode="lines",
    line=dict(color=BRAND['dark'], width=2.8),
    fill="tozeroy", fillcolor=rgba(BRAND['orange'], 0.25), name="누적 매출"
))
apply_brand_layout(fig4, "누적 매출 추세", "누적 매출액(원)")
st.plotly_chart(fig4, use_container_width=True, theme="streamlit")

# 5) 최고·최저 강조
max_idx = int(pd.Series(sales).idxmax())
min_idx = int(pd.Series(sales).idxmin())

def pick_color(i):
    if i == max_idx:
        return rgba(BRAND['orange'], 0.98)
    if i == min_idx:
        return rgba(BRAND['dark'], 0.95)
    return rgba(BRAND['beige'], 0.5)

fig5 = go.Figure(go.Bar(x=labels, y=sales, marker_color=[pick_color(i) for i in range(len(sales))]))
apply_brand_layout(fig5, "월별 매출 (최고·최저 강조)", "매출액(원)")
st.plotly_chart(fig5, use_container_width=True, theme="streamlit")

# 데이터 다운로드
with st.expander("📥 정규화된 데이터 다운로드"):
    out_csv = df.drop(columns=["_dt"]).copy()
    buff = io.BytesIO()
    buff.write(out_csv.to_csv(index=False).encode("utf-8-sig"))
    st.download_button(
        label="CSV 다운로드",
        data=buff.getvalue(),
        file_name="normalized_sales.csv",
        mime="text/csv",
    )

st.caption("© Streamlit + Plotly · Hover로 툴팁 확인, Drag로 확대, Double-click으로 리셋 · Brand colors: #D9DA03 #DDCCBB #6E6665 #231914 #EC792C")
