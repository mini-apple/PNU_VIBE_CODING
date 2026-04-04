import json
import os
from datetime import date

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from schemas.models import EconomyReport


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


ECONOMY_REPORT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """당신은 경제 뉴스 분석 전문가입니다.
주어진 뉴스 문서를 바탕으로 오늘의 주요 경제 동향 리포트를 작성하세요.

반드시 아래 JSON 형식으로만 응답하세요. 코드블록 없이 순수 JSON만 출력하세요.
{{
  "report_date": "YYYY-MM-DD",
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
  "key_indicators": ["코스피 XXXX", "원/달러 XXXX원"],
  "total_articles_analyzed": 0
}}

작성 요구사항:
- sections: "국내 경제", "글로벌 시장", "산업 동향" 등 2~3개 섹션
- 각 섹션의 articles에 반드시 원문 url 포함 (없으면 빈 문자열)
- key_indicators: 코스피, 코스닥, 원/달러 환율, 금리 등 수치 지표 3~5개
- headline_summary: 3줄 이내 핵심 요약
- 모든 내용은 한국어로 작성""",
        ),
        (
            "human",
            """오늘 날짜: {today}

뉴스 문서:
{docs}

위 내용을 바탕으로 경제 뉴스 리포트를 JSON 형식으로 작성하세요.""",
        ),
    ]
)


def generate_economy_news_report(docs: list[dict]) -> EconomyReport:
    llm = _get_llm()
    parser = JsonOutputParser()
    chain = ECONOMY_REPORT_PROMPT | llm | parser

    result = chain.invoke(
        {
            "today": date.today().isoformat(),
            "docs": json.dumps(docs, ensure_ascii=False, indent=2),
        }
    )

    return EconomyReport.model_validate(result)
