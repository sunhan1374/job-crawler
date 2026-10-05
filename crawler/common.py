"""여러 사이트가 함께 쓰는 도구: HTTP 요청, 지역 필터, 점수 계산."""
import re
import time

import requests

import config

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

_session = requests.Session()
_session.headers.update(HEADERS)


def http(method, url, **kw):
    """요청 한 번 + 예의상 쉬기. 실패하면 예외를 그대로 올려서 사이트별로 처리."""
    kw.setdefault("timeout", 20)
    for attempt in range(3):
        r = _session.request(method, url, **kw)
        time.sleep(config.REQUEST_DELAY)
        # 429 = "너무 자주 요청함". 잠시 쉬었다가 최대 2번 다시 시도합니다.
        if r.status_code != 429:
            break
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    return r


# ── 지역 ────────────────────────────────────────────────
def region_ok(location: str) -> bool:
    """'서울 강남구', '경기 성남시 분당구' 같은 문자열이 희망 근무지인지."""
    if not location:
        return False
    loc = location.replace("특별시", "").replace("광역시", "")
    if config.SEOUL and "서울" in loc:
        return True
    if "경기" in loc:
        return any(city in loc for city in config.GYEONGGI_SOUTH)
    return False


def short_location(location: str) -> str:
    """'서울전체, 강남구, 서초구' → '서울 강남구 외' 처럼 한 곳으로 줄여 보여줍니다."""
    loc = (location or "").replace("서울특별시", "서울").replace("경기도", "경기")
    parts = [re.sub(r"\s+", " ", p).strip() for p in loc.split(",") if p.strip()]
    if not parts:
        return ""
    first = re.sub(r"(서울|경기)\s*\1?전체", r"\1", parts[0]).replace(" 전체", "").strip()
    rest = parts[1:]
    if first in ("서울", "경기") and rest and not re.match(r"(서울|경기)", rest[0]):
        first += " " + rest.pop(0)
    return first + (" 외" if rest else "")


# ── 직군 분류 & 점수 ─────────────────────────────────────
_T1 = re.compile(config.TIER1, re.I)
_T2 = re.compile(config.TIER2, re.I)
_DOM = re.compile(config.DOMAIN, re.I)
_EXC = re.compile(config.EXCLUDE, re.I)


def classify(title: str):
    """공고 제목 → '기술지원' / '추천 직군' / None(제외)."""
    if not title or _EXC.search(title):
        return None
    if _T1.search(title):
        return "기술지원"
    if _T2.search(title):
        return "추천 직군"
    return None


def score(job: dict) -> int:
    """0~100 적합도. 이유(reasons)도 같이 채워 화면에서 보여줍니다."""
    s, why = 0, []
    if job["tier"] == "기술지원":
        s += 50
        why.append("기술지원 직무")
    else:
        s += 30
        why.append("인접 직무")

    text = f'{job["title"]} {job["company"]}'
    if _DOM.search(text):
        s += 20
        why.append("결제·핀테크 도메인")

    lo, hi = job.get("exp_min"), job.get("exp_max")
    me = config.MY_YEARS
    if job.get("newbie_only"):
        s -= 30
        why.append("신입 전용")
    elif lo is not None or hi is not None:
        lo_ = lo if lo is not None else 0
        hi_ = hi if hi is not None else 99
        if lo_ <= me <= hi_:
            s += 15
            why.append("경력 조건 맞음")
        elif hi_ < 5:
            s -= 20
            why.append("주니어 대상")
        elif lo_ > me + 3:
            s -= 10
            why.append("요구 경력 높음")

    r = job.get("rating")
    if r is not None:
        if r >= 3.5:
            s += 15
            why.append(f"평점 {r}")
        elif r >= 3.0:
            s += 5
        elif r < 2.5:
            s -= 10
            why.append(f"평점 낮음 {r}")

    job["score"] = max(0, min(100, s))
    job["reasons"] = why
    return job["score"]


def exp_text(lo, hi, newbie=False):
    if newbie:
        return "신입"
    if lo is None and hi is None:
        return "경력무관"
    if hi is None or hi >= 50:
        return f"{lo}년↑" if lo else "경력무관"
    return f"{lo or 0}~{hi}년"


def clean_company(name: str) -> str:
    """'(주)카카오페이', '이스트소프트(ESTsoft)' → '카카오페이', '이스트소프트' (검색용 회사명)."""
    n = (name or "").replace("（", "(").replace("）", ")")
    n = re.sub(r"\(주\)|㈜|주식회사|\(유\)|유한회사|\(재\)|\(사\)|^주\)\s*", "", n)
    n = re.sub(r"\([^)]*(\)|$)", "", n)  # 괄호 속 영문명/브랜드명 제거
    n = re.sub(r"\b(inc|corp|co|ltd)\b\.?", "", n, flags=re.I)
    return re.sub(r"\s+", " ", n).strip()


def norm_company(name: str) -> str:
    return re.sub(r"[\s·\-_.,]", "", clean_company(name)).lower()


def norm_title(title: str) -> str:
    return re.sub(r"[\s\[\]()·\-_/,.|]", "", (title or "")).lower()
