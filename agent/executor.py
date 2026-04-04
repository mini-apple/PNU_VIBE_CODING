import json
import logging
import os
import re

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from agent.prompts import FIELD_SYSTEM_PROMPT, ECONOMY_SYSTEM_PROMPT
from agent.tools import (
    search_news,
    store_articles_to_vectordb,
    query_vectordb,
    generate_field_report,
    generate_economy_report,
)
from constants import ECONOMY_QUERIES
from schemas.models import FieldNewsReport, EconomyReport, UserProfile
from search.query_builder import build_field_queries

logger = logging.getLogger(__name__)


def _create_executor(tools: list[BaseTool], system_prompt: str) -> AgentExecutor:
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-5-mini"),
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=12,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )


def _extract_tool_output(intermediate_steps: list, tool_name: str) -> str | None:
    """중간 단계에서 특정 Tool의 마지막 반환값을 추출합니다."""
    result = None
    for action, observation in intermediate_steps:
        if hasattr(action, "tool") and action.tool == tool_name:
            result = observation
    return result


def _parse_json_from_text(text: str) -> str:
    """텍스트에서 JSON 객체를 추출합니다."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group()
    return text


def run_field_agent(profile: UserProfile) -> FieldNewsReport:
    """분야 뉴스 AgentExecutor를 실행하고 FieldNewsReport를 반환합니다."""
    queries = build_field_queries(profile)
    executor = _create_executor(
        tools=[search_news, store_articles_to_vectordb, query_vectordb, generate_field_report],
        system_prompt=FIELD_SYSTEM_PROMPT,
    )

    input_text = f"""
지원 분야: {profile.field}
관심 기업: {json.dumps(profile.companies, ensure_ascii=False)}
검색 쿼리: {json.dumps(queries, ensure_ascii=False)}

위 정보를 활용해 지원 분야 뉴스 리포트를 생성해주세요.
"""
    result = executor.invoke({"input": input_text})

    # 중간 단계에서 generate_field_report 결과 우선 추출
    report_json = _extract_tool_output(
        result.get("intermediate_steps", []), "generate_field_report"
    )
    if not report_json:
        report_json = _parse_json_from_text(result.get("output", "{}"))

    try:
        return FieldNewsReport.model_validate_json(report_json)
    except Exception as e:
        logger.error("FieldNewsReport 파싱 실패: %s\n원본: %s", e, report_json[:300])
        raise


def run_economy_agent() -> EconomyReport:
    """경제 뉴스 AgentExecutor를 실행하고 EconomyReport를 반환합니다."""
    executor = _create_executor(
        tools=[search_news, store_articles_to_vectordb, query_vectordb, generate_economy_report],
        system_prompt=ECONOMY_SYSTEM_PROMPT,
    )

    input_text = f"""
경제 뉴스 검색 쿼리: {json.dumps(ECONOMY_QUERIES, ensure_ascii=False)}

위 쿼리를 활용해 오늘의 경제 뉴스 리포트를 생성해주세요.
"""
    result = executor.invoke({"input": input_text})

    report_json = _extract_tool_output(
        result.get("intermediate_steps", []), "generate_economy_report"
    )
    if not report_json:
        report_json = _parse_json_from_text(result.get("output", "{}"))

    try:
        return EconomyReport.model_validate_json(report_json)
    except Exception as e:
        logger.error("EconomyReport 파싱 실패: %s\n원본: %s", e, report_json[:300])
        raise
