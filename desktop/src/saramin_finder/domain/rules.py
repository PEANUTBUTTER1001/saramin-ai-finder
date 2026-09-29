from __future__ import annotations

import re

from saramin_finder.domain.models import SearchProfile


REGION_OPTIONS = (
    ("101000", "서울 전체"), ("102000", "경기 전체"),
    ("108000", "인천 전체"), ("103000", "광주 전체"),
    ("104000", "대구 전체"), ("105000", "대전 전체"),
    ("106000", "부산 전체"), ("107000", "울산 전체"),
    ("109000", "강원 전체"), ("110000", "경남 전체"),
    ("111000", "경북 전체"), ("112000", "전남·광주 전체"),
    ("113000", "전북 전체"), ("114000", "충북 전체"),
    ("115000", "충남 전체"), ("116000", "제주 전체"),
    ("118000", "세종"),
)


def validate_profile(profile: SearchProfile) -> SearchProfile:
    regions = [code for code, _ in REGION_OPTIONS]
    if (len(profile.location_codes) != len(set(profile.location_codes)) or
            any(code not in regions for code in profile.location_codes)):
        raise ValueError("지역은 화면에 표시된 지역에서 중복 없이 선택해 주세요.")
    if (len(profile.experience_codes) != len(set(profile.experience_codes)) or
            any(code not in ("1", "2") for code in profile.experience_codes)):
        raise ValueError("경력 조건은 신입·경력 중에서 선택해 주세요.")
    if profile.experience_max is not None and (
            isinstance(profile.experience_max, bool) or
            not isinstance(profile.experience_max, int) or
            not 0 <= profile.experience_max <= 30 or
            "2" not in profile.experience_codes):
        raise ValueError("최대 경력은 경력을 선택한 경우 0~30년으로 입력해 주세요.")
    if (len(profile.education_codes) != len(set(profile.education_codes)) or
            any(code not in ("0", "8") for code in profile.education_codes)):
        raise ValueError("학력은 학력무관·4년제 대졸 중에서 선택해 주세요.")
    if profile.sort not in ("relation", "reg_dt") or profile.watch_pages not in (1, 3, 10):
        raise ValueError("지원하지 않는 검색 설정입니다.")
    return profile

SECTION_LABELS = {
    "main_work": ("주요업무", "주요 업무", "담당업무", "담당 업무", "포지션 상세"),
    "qualification": ("자격요건", "자격 요건", "지원자격", "지원 자격", "필수요건", "필수 요건"),
    "preference": ("우대사항", "우대 사항", "우대조건", "우대 조건"),
}
STOP_LABELS = (
    "혜택 및 복지", "복리후생", "근무환경", "전형절차", "유의사항",
    "접수기간", "지원방법", "근무조건", "기업정보", "채용절차",
)

# Ported from Android TechKeywords.kt. A hit counts once per posting and section.
KEYWORD_PATTERNS = {
    "n8n": (r"n8n",), "Harness": (r"하네스",),
    "PyTorch": (r"PyTorch", r"파이토치"),
    "TensorFlow": (r"TensorFlow", r"텐서플로(?:우)?"),
    "LLM": (r"\bLLM\b", r"거대\s*언어\s*모델"),
    "RAG": (r"\bRAG\b", r"검색\s*증강\s*생성"),
    "Deep Learning": (r"Deep\s*Learning", r"딥\s*러닝"),
    "Machine Learning": (r"Machine\s*Learning", r"머신\s*러닝"),
    "Computer Vision": (r"Computer\s*Vision", r"컴퓨터\s*비전"),
    "NLP": (r"\bNLP\b", r"자연어\s*처리"),
    "LangChain": (r"LangChain", r"랭체인"),
    "LangGraph": (r"LangGraph", r"랭그래프"),
    "Python": (r"Python", r"파이썬"),
    "Java": (r"\bJava\b", r"자바(?!스크립트)"),
    "Kotlin": (r"Kotlin", r"코틀린"),
    "TypeScript": (r"TypeScript", r"타입스크립트", r"\bTS\b"),
    "JavaScript": (r"JavaScript", r"자바스크립트", r"\bJS\b"),
    "MySQL": (r"MySQL", r"마이SQL"),
    "PostgreSQL": (r"PostgreSQL", r"포스트그레"),
    "Redis": (r"Redis", r"레디스"),
    "MongoDB": (r"MongoDB", r"몽고디비"),
    "Elasticsearch": (r"Elasticsearch", r"엘라스틱서치"),
    "SQL": (r"\bSQL\b", r"에스큐엘"),
    "Spring Boot": (r"Spring\s*Boot", r"스프링\s*부트"),
    "Spring": (r"\bSpring\b", r"스프링"),
    "Node.js": (r"Node\.?js", r"노드"),
    "Django": (r"Django", r"장고"),
    "FastAPI": (r"FastAPI", r"패스트API"),
    "React": (r"\bReact\b", r"리액트"),
    "Next.js": (r"Next\.?js", r"넥스트js"),
    "AWS": (r"\bAWS\b", r"아마존웹서비스"),
    "GCP": (r"\bGCP\b", r"구글클라우드"),
    "Docker": (r"Docker", r"도커"),
    "Kubernetes": (r"Kubernetes", r"쿠버네티스", r"k8s"),
    "Git": (r"\bGit\b", r"깃"),
    "Linux": (r"Linux", r"리눅스"),
}
COMPILED_KEYWORDS = {
    name: tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)
    for name, patterns in KEYWORD_PATTERNS.items()
}


def normalize_query(query: str) -> str:
    return " ".join(query.casefold().split())


def sector_keywords(sector: str) -> tuple[str, ...]:
    """Keep distinct, nonempty comma-separated job fields in display order."""
    return tuple(dict.fromkeys(part.strip() for part in sector.split(",") if part.strip()))


def validate_query(query: str) -> str:
    result = " ".join(query.split())
    if not result or len(result) > 40:
        raise ValueError("검색어는 1~40자로 입력해 주세요.")
    return result


def validate_interval(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("확인 간격은 1 이상의 정수(분)여야 합니다.")
    return value


def keywords_in(text: str) -> list[str]:
    return [name for name, patterns in COMPILED_KEYWORDS.items()
            if any(pattern.search(text) for pattern in patterns)]


def valid_education(conditions: list[str], selected_codes: tuple[str, ...] = ("0", "8")) -> bool:
    if not selected_codes:
        return True
    return any(
        ("0" in selected_codes and "학력" in item and "무관" in item)
        or ("8" in selected_codes and
            (("대졸" in item and "초대졸" not in item) or
             ("대학교" in item and "4년" in item)))
        for item in conditions
    )


def valid_job(sector: str, title: str, query: str) -> bool:
    term = query.upper()
    source = (sector + " " + title).upper()
    if any(word in term for word in ("AI", "인공지능", "인공 지능")):
        return any(word in source for word in ("AI", "인공지능", "인공 지능"))
    return term in source


def _line_kind(line: str) -> str | None:
    candidate = line.strip(" \t📋•●■□-:：")
    for kind, labels in SECTION_LABELS.items():
        if any(candidate.startswith(label) and len(candidate) <= len(label) + 12 for label in labels):
            return kind
    if any(candidate.startswith(label) and len(candidate) <= len(label) + 12 for label in STOP_LABELS):
        return "stop"
    return None


def extract_sections(full_text: str) -> tuple[dict[str, str], dict[str, str]]:
    sections = {kind: "" for kind in SECTION_LABELS}
    statuses = {kind: "missing" for kind in SECTION_LABELS}
    current: str | None = None
    collected: dict[str, list[str]] = {kind: [] for kind in SECTION_LABELS}
    for raw_line in full_text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        kind = _line_kind(line)
        if kind is not None:
            current = kind if kind != "stop" else None
            if current is not None:
                statuses[current] = "empty"
            continue
        if current is not None:
            collected[current].append(line)
    for kind, lines in collected.items():
        if lines:
            sections[kind] = "\n".join(lines)
            statuses[kind] = "extracted"
        elif statuses[kind] == "missing" and any(label in full_text for label in SECTION_LABELS[kind]):
            statuses[kind] = "ambiguous"
    return sections, statuses
