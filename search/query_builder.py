from schemas.models import UserProfile
from constants import FIELD_PRESET_QUERIES


def build_field_queries(profile: UserProfile) -> list[str]:
    """지원 분야·관심 기업·추가 키워드를 기반으로 뉴스 검색 쿼리를 생성합니다."""
    base_queries = list(
        FIELD_PRESET_QUERIES.get(profile.field, [f"{profile.field} 최신 뉴스 동향"])
    )

    for company in profile.companies[:3]:
        base_queries.append(f"{company} {profile.field} 최신 뉴스")

    for keyword in profile.extra_keywords[:2]:
        base_queries.append(f"{keyword} 최신 동향 뉴스")

    return base_queries
