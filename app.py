import calendar
import logging
from datetime import date

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from schemas.models import (
    EconomyReport,
    FieldNewsReport,
    NewsArticle,
    UserProfile,
)

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="뉴스 수집 AI Agent",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("### 📰 취준생을 위한 뉴스 수집 요약 AI Agent")
st.divider()


# ── 달력 유틸 ─────────────────────────────────────────────────────────────────


def build_calendar_html(year: int, month: int, today_day: int) -> str:
    """월 달력을 고정 너비 HTML 테이블로 반환합니다."""
    weeks = calendar.monthcalendar(year, month)
    day_headers = ["월", "화", "수", "목", "금", "토", "일"]

    rows = ""
    for week in weeks:
        cells = ""
        for col, day in enumerate(week):
            if day == 0:
                cells += "<td>&nbsp;</td>"
            elif day == today_day:
                cells += (
                    f"<td><div class='cal-today'>{day}</div></td>"
                )
            elif col == 5:
                cells += f"<td style='color:#e55353;'>{day}</td>"
            elif col == 6:
                cells += f"<td style='color:#4a90d9;'>{day}</td>"
            else:
                cells += f"<td>{day}</td>"
        rows += f"<tr>{cells}</tr>"

    header_cells = "".join(
        f"<th style='color:#e55353;'>{d}</th>" if i == 5
        else f"<th style='color:#4a90d9;'>{d}</th>" if i == 6
        else f"<th>{d}</th>"
        for i, d in enumerate(day_headers)
    )

    return f"""
    <style>
      .cal-table {{
        width: 100%; table-layout: fixed; border-collapse: collapse;
        font-size: 0.82rem; text-align: center;
      }}
      .cal-table th, .cal-table td {{
        width: 14.28%; padding: 5px 0;
        box-sizing: border-box;
      }}
      .cal-table th {{ color:#999; font-weight:500; padding-bottom:6px; }}
      .cal-today {{
        background: #FF4B4B; color: #fff; border-radius: 50%;
        width: 22px; height: 22px; line-height: 22px;
        font-weight: 700; margin: 0 auto;
      }}
    </style>
    <table class="cal-table">
      <thead><tr>{header_cells}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """


# ── 날씨 유틸 ─────────────────────────────────────────────────────────────────

_WEATHER_EMOJI = {
    113: "☀️", 116: "⛅", 119: "☁️", 122: "🌫️",
    143: "🌫️", 248: "🌫️", 260: "🌫️",
    176: "🌦️", 293: "🌦️", 296: "🌦️",
    299: "🌧️", 302: "🌧️", 305: "🌧️", 308: "🌧️",
    311: "🌧️", 314: "🌧️", 317: "🌨️", 320: "🌨️",
    200: "⛈️", 386: "⛈️", 389: "⛈️",
    227: "❄️", 230: "❄️", 323: "❄️", 326: "❄️",
    329: "❄️", 332: "❄️", 335: "❄️", 338: "❄️",
}


@st.cache_data(ttl=1800)
def fetch_weather(city: str = "Busan") -> dict:
    """wttr.in JSON API로 날씨 정보를 가져옵니다 (API 키 불필요)."""
    try:
        import requests

        resp = requests.get(
            f"https://wttr.in/{city}?format=j1", timeout=5
        )
        if resp.status_code == 200:
            cur = resp.json()["current_condition"][0]
            code = int(cur["weatherCode"])
            return {
                "emoji": _WEATHER_EMOJI.get(code, "🌡️"),
                "desc": cur["weatherDesc"][0]["value"],
                "temp": cur["temp_C"],
                "feels": cur["FeelsLikeC"],
                "humidity": cur["humidity"],
            }
    except Exception:
        pass
    return {}


# ── 사이드바: 날짜 · 달력 · 날씨 ─────────────────────────────────────────────

with st.sidebar:
    today = date.today()
    weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]

    # 날짜 — 한 줄로
    st.markdown(
        f"<div style='text-align:center; font-size:0.95rem; font-weight:600;"
        f"padding: 6px 0; color:#333;'>"
        f"{today.year}년 {today.month}월 {today.day}일 {weekdays_kr[today.weekday()]}요일"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # 달력
    st.markdown(
        build_calendar_html(today.year, today.month, today.day),
        unsafe_allow_html=True,
    )

    st.divider()

    # 날씨 (부산 고정, wttr.in JSON API)
    w = fetch_weather("Busan")
    if w:
        st.markdown(
            f"""
            <div style='text-align:center; padding:10px 0;'>
              <div style='font-size:0.78rem; color:#aaa; margin-bottom:4px;'>📍 부산 날씨</div>
              <div style='font-size:1.6rem;'>{w['emoji']}</div>
              <div style='font-size:1.1rem; font-weight:700; color:#333;'>{w['temp']}°C</div>
              <div style='font-size:0.8rem; color:#555;'>{w['desc']}</div>
              <div style='font-size:0.75rem; color:#999; margin-top:3px;'>
                체감 {w['feels']}°C &nbsp;·&nbsp; 습도 {w['humidity']}%
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption("날씨 정보를 불러올 수 없습니다.")


# ── 공통 렌더 헬퍼 ────────────────────────────────────────────────────────────


def render_articles(articles: list[NewsArticle]) -> None:
    for a in articles:
        if a.url:
            st.markdown(f"- **[{a.title}]({a.url})** ({a.source})")
        else:
            st.markdown(f"- **{a.title}** ({a.source})")
        st.caption(a.one_line_summary)


# ── TAB 1: 직무 특화 뉴스 렌더 ───────────────────────────────────────────────


def render_field_report(report: FieldNewsReport) -> None:
    st.markdown(f"#### 📅 {report.report_date}  |  분야: **{report.target_field}**")
    if report.target_companies:
        st.markdown(f"관심 기업: {', '.join(report.target_companies)}")
    st.info(report.headline_summary)

    for section in report.sections:
        with st.expander(f"📌 {section.section_title}", expanded=True):
            st.markdown(section.content)
            if section.articles:
                st.markdown("**관련 기사**")
                render_articles(section.articles)

    if report.key_takeaways:
        st.markdown("### 💡 핵심 인사이트")
        for item in report.key_takeaways:
            st.markdown(f"- {item}")

    st.caption(f"분석 기사 수: {report.total_articles_analyzed}건")


# ── TAB 2: 경제 뉴스 렌더 ────────────────────────────────────────────────────


def render_economy_report(report: EconomyReport) -> None:
    st.markdown(f"#### 📅 {report.report_date}")
    st.info(report.headline_summary)

    for section in report.sections:
        with st.expander(f"📌 {section.section_title}", expanded=True):
            st.markdown(section.content)
            if section.articles:
                st.markdown("**관련 기사**")
                render_articles(section.articles)

    st.caption(f"분석 기사 수: {report.total_articles_analyzed}건")


# ── 메인 탭 ───────────────────────────────────────────────────────────────────

tab_field, tab_economy = st.tabs(["🗂 직무 특화 뉴스", "💹 경제 뉴스"])

# ── TAB 1: 직무 특화 뉴스 ────────────────────────────────────────────────────

with tab_field:
    # 프로필 입력 폼
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            field_raw = st.text_input(
                "관심 분야",
                placeholder="예: 반도체, IT",
                key="field_input",
            )
        with col2:
            companies_raw = st.text_input(
                "관심 기업 (쉼표 구분)",
                placeholder="예: 삼성전자, SK하이닉스",
                key="companies_input",
            )
        with col3:
            extra_raw = st.text_input(
                "추가 키워드 (선택)",
                placeholder="예: HBM, 파운드리",
                key="extra_input",
            )

    field = field_raw.strip() or "IT"
    companies = [c.strip() for c in companies_raw.split(",") if c.strip()]
    extra_keywords = [k.strip() for k in extra_raw.split(",") if k.strip()]

    field_btn = st.button(
        "🚀 직무 특화 뉴스 수집 시작",
        key="btn_field",
        type="primary",
        use_container_width=True,
    )

    if field_btn:
        from rag.vectorstore import reset_client
        from agent.executor import run_field_agent

        profile = UserProfile(field=field, companies=companies, extra_keywords=extra_keywords)
        reset_client()

        with st.spinner(f"'{profile.field}' 관련 최신 뉴스 수집 중..."):
            try:
                report = run_field_agent(profile)
                st.session_state["field_report"] = report
                st.session_state["field_error"] = None
            except Exception as e:
                st.session_state["field_report"] = None
                st.session_state["field_error"] = str(e)

    if st.session_state.get("field_error"):
        st.error(f"오류가 발생했습니다: {st.session_state['field_error']}")
    elif st.session_state.get("field_report"):
        render_field_report(st.session_state["field_report"])
    else:
        st.info(
            "**관심 분야**와 관심 기업을 입력한 뒤 버튼을 눌러주세요.\n\n"
            "예시: 반도체, AI, 바이오, 금융, 게임"
        )

# ── TAB 2: 경제 뉴스 ─────────────────────────────────────────────────────────

with tab_economy:
    economy_btn = st.button(
        "🚀 경제 뉴스 수집 시작",
        key="btn_economy",
        type="primary",
        use_container_width=True,
    )

    if economy_btn:
        from rag.vectorstore import reset_client
        from agent.executor import run_economy_agent

        reset_client()

        with st.spinner("경제 뉴스 수집 중..."):
            try:
                report = run_economy_agent()
                st.session_state["economy_report"] = report
                st.session_state["economy_error"] = None
            except Exception as e:
                st.session_state["economy_report"] = None
                st.session_state["economy_error"] = str(e)

    if st.session_state.get("economy_error"):
        st.error(f"오류가 발생했습니다: {st.session_state['economy_error']}")
    elif st.session_state.get("economy_report"):
        render_economy_report(st.session_state["economy_report"])
    else:
        st.info(
            "위 버튼을 눌러주세요.\n\n"
            "코스피·코스닥, 환율, 금리, 주요 기업 실적 등 오늘의 경제 동향을 요약합니다."
        )
