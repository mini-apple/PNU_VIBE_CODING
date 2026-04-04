import json
import os
from datetime import date

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from schemas.models import FieldNewsReport


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


FIELD_REPORT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """당신은 취업 준비생을 위한 지원 분야 뉴스 분석 전문가입니다.
주어진 뉴스 문서를 바탕으로 지원 분야의 최신 산업 트렌드와 핵심 인사이트를 담은 리포트를 작성하세요.

반드시 아래 JSON 형식으로만 응답하세요. 코드블록 없이 순수 JSON만 출력하세요.
{{
  "report_date": "YYYY-MM-DD",
  "target_field": "지원 분야명",
  "target_companies": ["기업1", "기업2"],
  "headline_summary": "3줄 이내 핵심 요약",
  "sections": [
    {{
      "section_title": "섹션 제목",
      "content": "섹션 본문",
      "articles": [
        {{
          "title": "기사 제목",
          "url": "https://...",
          "source": "언론사",
          "one_line_summary": "한 줄 요약"
        }}
      ]
    }}
  ],
  "key_takeaways": ["인사이트1", "인사이트2"],
  "total_articles_analyzed": 0
}}

작성 요구사항:
- sections: "산업 트렌드", "기술 동향", "주요 기업 이슈" 등 2~3개 섹션
- 각 섹션의 articles에 반드시 원문 url 포함 (없으면 빈 문자열)
- key_takeaways: 취준생 관점의 핵심 인사이트 3~5개
- headline_summary: 3줄 이내
- 관심 기업 관련 내용이 있으면 우선 포함
- 모든 내용은 한국어로 작성""",
        ),
        (
            "human",
            """지원 분야: {field}
관심 기업: {companies}
오늘 날짜: {today}

뉴스 문서:
{docs}

위 내용을 바탕으로 분야 뉴스 리포트를 JSON 형식으로 작성하세요.""",
        ),
    ]
)


def generate_field_news_report(
    field: str,
    companies: list[str],
    docs: list[dict],
) -> FieldNewsReport:
    llm = _get_llm()
    parser = JsonOutputParser()
    chain = FIELD_REPORT_PROMPT | llm | parser

    result = chain.invoke(
        {
            "field": field,
            "companies": ", ".join(companies) if companies else "없음",
            "today": date.today().isoformat(),
            "docs": json.dumps(docs, ensure_ascii=False, indent=2),
        }
    )

    return FieldNewsReport.model_validate(result)
