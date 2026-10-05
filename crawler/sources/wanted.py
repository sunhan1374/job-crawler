"""원티드 — 사이트가 화면에 쓰는 공개 JSON(API v4)을 그대로 읽습니다."""
from urllib.parse import quote

import config
from common import http

API = "https://www.wanted.co.kr/api/v4/jobs"


def fetch():
    jobs = []
    for kw in config.KEYWORDS:
        for page in range(config.MAX_PAGES):
            url = (
                f"{API}?country=kr&job_sort=job.latest_order&locations=all&years=-1"
                f"&limit=100&offset={page * 100}&query={quote(kw)}"
            )
            data = http("GET", url, headers={"Referer": "https://www.wanted.co.kr/"}).json()
            rows = data.get("data") or []
            for d in rows:
                jobs.append(parse(d))
            if not (data.get("links") or {}).get("next") or not rows:
                break
    return jobs


def parse(d):
    addr = d.get("address") or {}
    lo, hi = d.get("annual_from"), d.get("annual_to")
    return {
        "source": "wanted",
        "source_id": str(d["id"]),
        "company": (d.get("company") or {}).get("name", ""),
        "location": f'{addr.get("location") or ""} {addr.get("district") or ""}'.strip(),
        "title": d.get("position", ""),
        "url": f'https://www.wanted.co.kr/wd/{d["id"]}',
        "exp_min": lo,
        "exp_max": None if (hi is None or hi >= 50) else hi,
        "newbie_only": lo == 0 and hi == 0,
        "due": d.get("due_time") or "",
    }
