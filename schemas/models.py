from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    field: str
    companies: list[str] = Field(default_factory=list)
    extra_keywords: list[str] = Field(default_factory=list)


class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    published_date: Optional[str] = None
    summary: str
    keywords: list[str] = Field(default_factory=list)


class NewsArticle(BaseModel):
    title: str
    url: str
    source: str
    one_line_summary: str


# ── TAB 1: 분야 뉴스 ────────────────────────────────────────────────────

class FieldNewsSection(BaseModel):
    section_title: str
    content: str
    articles: list[NewsArticle]


class FieldNewsReport(BaseModel):
    report_date: str
    target_field: str
    target_companies: list[str]
    headline_summary: str
    sections: list[FieldNewsSection]
    key_takeaways: list[str]
    total_articles_analyzed: int


# ── TAB 2: 경제 뉴스 ────────────────────────────────────────────────────

class EconomyReportSection(BaseModel):
    section_title: str
    content: str
    articles: list[NewsArticle]


class EconomyReport(BaseModel):
    report_date: str
    headline_summary: str
    sections: list[EconomyReportSection]
    key_indicators: list[str]
    total_articles_analyzed: int
