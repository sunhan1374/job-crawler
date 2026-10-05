"""잡코리아 — 검색 결과 페이지에 함께 내려오는 공고 데이터(JSON)를 꺼내 읽습니다.

잡코리아 화면은 Next.js로 만들어져 있어서, HTML 안의
self.__next_f.push([1,"..."]) 조각들에 공고 목록 JSON이 들어 있습니다.
"""
import json
import re
from urllib.parse import quote

import config
from common import http

BASE = "https://www.jobkorea.co.kr"
_PUSH = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)</script>')
_AREA = {}  # 'I010' → '서울>강남구'


def _load_area_codes():
    if _AREA:
        return
    for c in http("GET", f"{BASE}/Search/api/codes/area").json():
        _AREA[c["code"]] = c.get("tagDisplayName") or c.get("displayName", "")


def fetch():
    _load_area_codes()
    jobs = []
    for kw in config.KEYWORDS:
        for page in range(1, config.MAX_PAGES + 2):  # 한 페이지 20건이라 1장 더
            url = f"{BASE}/Search/?stext={quote(kw)}&tabType=recruit&Page_No={page}"
            html = http("GET", url, headers={"Referer": BASE + "/"}).text
            rows = extract(html)
            jobs += [parse(d) for d in rows]
            if len(rows) < 20:
                break
    return jobs


def extract(html):
    """HTML → 공고 dict 목록."""
    s = "".join(json.loads(m) for m in _PUSH.findall(html))
    idx = 0
    while True:
        idx = s.find('"pageSize":', idx)
        if idx == -1:
            return []
        start = s.rfind("{", 0, idx)
        end = _match_brace(s, start)
        try:
            obj = json.loads(s[start:end + 1])
            content = obj.get("content") or []
            if content and "legacyJobNo" in content[0]:
                return content
        except (ValueError, AttributeError):
            pass
        idx = end + 1


def _match_brace(s, start):
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(s) - 1


def _location(codes):
    """희망 지역 코드를 우선으로 사람이 읽는 지역명 하나를 고릅니다."""
    names = [_AREA.get(c, "") for c in codes or []]
    names = [n.replace(">", " ") for n in names if n]
    for n in names:
        if n.startswith("서울") or n.startswith("경기"):
            from common import region_ok
            if region_ok(n):
                return n
    return names[0] if names else ""


def parse(d):
    ctype = str(d.get("careerType") or "")
    rng = d.get("careerRange")
    lo = rng if (ctype in ("2", "3") and isinstance(rng, int) and rng < 50) else None
    period = d.get("applicationPeriod") or {}
    due = (period.get("end") or "")[:10]
    if due.startswith("2070"):
        due = "상시채용"
    no = d["legacyJobNo"]
    return {
        "source": "jobkorea",
        "source_id": str(no),
        "company": d.get("postingCompanyName") or d.get("companyName", ""),
        "location": _location(d.get("areaCodeList")),
        "title": d.get("title", ""),
        "url": f"{BASE}/Recruit/GI_Read/{no}",
        "exp_min": lo,
        "exp_max": None,
        "newbie_only": ctype == "1",
        "due": due,
    }
