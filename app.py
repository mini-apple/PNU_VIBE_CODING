import logging

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


# ── 공통 렌더 헬퍼 ────────────────────────────────────────────────────────────


def render_articles(articles: list[NewsArticle]) -> None:
    for a in articles:
        if a.url:
            st.markdown(f"- **[{a.title}]({a.url})** ({a.source})")
        else:
            st.markdown(f"- **{a.title}** ({a.source})")
        st.caption(a.one_line_summary)


# ── TAB 1: 분야 뉴스 렌더 ────────────────────────────────────────────────────


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

    if report.key_indicators:
        cols = st.columns(min(len(report.key_indicators), 5))
        for col, indicator in zip(cols, report.key_indicators):
            col.metric(label="", value=indicator)

    for section in report.sections:
        with st.expander(f"📌 {section.section_title}", expanded=True):
            st.markdown(section.content)
            if section.articles:
                st.markdown("**관련 기사**")
                render_articles(section.articles)

    st.caption(f"분석 기사 수: {report.total_articles_analyzed}건")


# ── 사이드바: 프로필 입력만 ───────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ 프로필 설정")
    st.divider()

    field_raw = st.text_input(
        "관심 분야",
        placeholder="예: 반도체, IT",
    )
    field = field_raw.strip() or "IT"

    companies_raw = st.text_input(
        "관심 기업 (쉼표 구분)",
        placeholder="예: 삼성전자, SK하이닉스",
    )
    companies = [c.strip() for c in companies_raw.split(",") if c.strip()]

    extra_raw = st.text_input(
        "추가 키워드 (선택)",
        placeholder="예: HBM, 파운드리",
    )
    extra_keywords = [k.strip() for k in extra_raw.split(",") if k.strip()]


def _get_profile() -> UserProfile:
    return UserProfile(
        field=field,
        companies=companies,
        extra_keywords=extra_keywords,
    )


# ── 메인 탭 ───────────────────────────────────────────────────────────────────

tab_field, tab_economy = st.tabs(["📌 분야 뉴스", "💹 경제 뉴스"])

# ── TAB 1: 분야 뉴스 ─────────────────────────────────────────────────────────

with tab_field:
    field_btn = st.button(
        "🚀 분야 뉴스 수집 시작",
        key="btn_field",
        type="primary",
        use_container_width=True,
    )

    if field_btn:
        from rag.vectorstore import reset_client
        from agent.executor import run_field_agent

        profile = _get_profile()
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
            "사이드바에서 **관심 분야**와 관심 기업을 입력한 뒤 "
            "위 버튼을 눌러주세요.\n\n"
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
