"""잡플래닛 평점 — 회사명 자동완성으로 회사 ID를 찾고, 회사 페이지에서 평점을 읽습니다.

같은 회사를 매번 다시 찾지 않도록 data/ratings_cache.json 에 30일간 저장합니다.
(잡플래닛 robots.txt는 /search 수집을 막고 있어서, 검색 페이지 대신 자동완성+회사 페이지만 씁니다.)

오매칭 방지: 회사명이 '정확히' 같을 때만 평점을 붙입니다.
(예: 'CJ올리브네트웍스'가 'CJ올리브네트웍스 부산용호점'에 붙는 일을 막기 위해)
"""
import json
import os
import re
import time
from datetime import date, timedelta
from urllib.parse import quote

import config
from common import clean_company, http, norm_company

BASE = "https://www.jobplanet.co.kr"
CACHE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ratings_cache.json")
KEEP_DAYS = 30

# 회사 페이지 안의 검색엔진용 데이터(JSON-LD) → 가장 안정적
_LD_VALUE = re.compile(r"ratingValue\W{1,12}([0-9.]+)")
_LD_COUNT = re.compile(r"ratingCount\W{1,12}(\d+)")
# 화면에 보이는 큰 평점 숫자 → 예비용
_RATE_SPAN = re.compile(r'class="rate_point[^"]*"[^>]*>\s*([0-9.]+)\s*<')
_TITLE_COUNT = re.compile(r"기업리뷰\s*([\d,]+)건")


def load_cache():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)


def parse_rating(html):
    """회사 페이지 HTML → (평점, 리뷰 수). 리뷰가 없으면 (None, 0)."""
    count = None
    m = _LD_COUNT.search(html) or _TITLE_COUNT.search(html)
    if m:
        count = int(m.group(1).replace(",", ""))
    m = _LD_VALUE.search(html) or _RATE_SPAN.search(html)
    rating = float(m.group(1)) if m else None
    if not rating or count == 0:  # 0.0 은 '리뷰 없음'
        return None, count or 0
    return rating, count


# 한 번 실행할 때의 상태: 잡플래닛이 막았는지, 새로 몇 곳을 조회했는지
STATE = {"blocked": False, "new_lookups": 0}


def lookup(company, cache):
    """회사명 → {'id', 'name', 'rating', 'count'} 또는 None. 캐시 우선.

    잡플래닛이 403/429로 막으면 그 즉시 이번 실행의 조회를 멈춥니다(서킷 브레이커).
    한 번에 새로 조회하는 회사 수도 제한해서, 며칠에 걸쳐 조금씩 평점을 채웁니다.
    """
    key = norm_company(company)
    if not key:
        return None
    hit = cache.get(key)
    if hit and hit.get("checked", "") >= str(date.today() - timedelta(days=KEEP_DAYS)):
        return hit if hit.get("id") else None
    if STATE["blocked"] or STATE["new_lookups"] >= config.JOBPLANET_MAX_NEW:
        # 오래된 캐시라도 있으면 그걸 쓰고, 없으면 다음 실행 때 조회
        return hit if hit and hit.get("id") else None

    STATE["new_lookups"] += 1
    result = {"checked": str(date.today())}
    try:
        time.sleep(config.JOBPLANET_DELAY)
        term = quote(clean_company(company))
        data = http("GET", f"{BASE}/autocomplete/autocomplete/suggest.json?term={term}").json()
        best = next((c for c in data.get("companies") or []
                     if norm_company(c.get("name", "")) == key), None)
        if best:
            rating, count = parse_rating(http("GET", f'{BASE}/companies/{best["id"]}').text)
            result.update(id=best["id"], name=best.get("name"), rating=rating, count=count)
    except Exception as e:  # 평점은 부가 정보라 실패해도 전체 수집은 계속
        code = getattr(getattr(e, "response", None), "status_code", None)
        if code in (403, 429):
            STATE["blocked"] = True
            print(f"   · 잡플래닛이 요청을 막았어요({code}). 이번 실행의 평점 조회는 여기서 멈추고 다음에 이어서 해요.")
        else:
            print(f"   · 잡플래닛 조회 실패({company}): {e}")
        return hit if hit and hit.get("id") else None
    cache[key] = result
    return result if result.get("id") else None
