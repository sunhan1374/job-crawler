"""리멤버 — 공고 목록 화면이 호출하는 검색 API(POST)를 사용합니다. 로그인 불필요."""
import config
from common import http

API = "https://career-api.rememberapp.co.kr/job_postings/search"


def fetch():
    jobs = []
    for kw in config.KEYWORDS:
        for page in range(1, config.MAX_PAGES + 1):
            body = {"search": {"keywords": [kw]}, "page": page, "per": 50}
            data = http(
                "POST", API, json=body,
                headers={"Origin": "https://career.rememberapp.co.kr",
                         "Referer": "https://career.rememberapp.co.kr/"},
            ).json()
            rows = data.get("data") or []
            jobs += [parse(d) for d in rows]
            meta = data.get("meta") or {}
            if not rows or page >= (meta.get("total_pages") or 0):
                break
    return jobs


def parse(d):
    org = d.get("organization") or {}
    addrs = d.get("addresses") or []
    a = addrs[0] if addrs else {}
    loc = f'{a.get("address_level1", "")} {a.get("address_level2", "")}'.strip()
    return {
        "source": "remember",
        "source_id": str(d["id"]),
        "company": org.get("name", ""),
        "headhunter": bool(org.get("headhunter")),
        "location": loc,
        "title": d.get("title", ""),
        "url": f'https://career.rememberapp.co.kr/job/posting/{d["id"]}',
        "exp_min": d.get("min_experience"),
        "exp_max": d.get("max_experience"),
        "newbie_only": False,
        "due": (d.get("ends_at") or "")[:10] if d.get("explicit_due") else "",
    }
