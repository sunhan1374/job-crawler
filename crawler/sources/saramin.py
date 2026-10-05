"""사람인 — 검색 결과 HTML을 읽습니다(API 키 불필요). 서울(101000)+경기(102000)로 좁혀 검색."""
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

import config
from common import http

SEARCH = "https://www.saramin.co.kr/zf_user/search/recruit"


def fetch():
    jobs = []
    for kw in config.KEYWORDS:
        for page in range(1, config.MAX_PAGES + 1):
            url = (
                f"{SEARCH}?searchType=search&searchword={quote(kw)}"
                f"&loc_mcd=101000%2C102000&recruitPage={page}"
                f"&recruitSort=reg_dt&recruitPageCount=100"
            )
            html = http("GET", url).text
            rows = parse_page(html)
            jobs += rows
            if len(rows) < 100:
                break
    return jobs


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for it in soup.select("div.item_recruit"):
        rec = it.get("value")
        a = it.select_one(".job_tit a")
        corp = it.select_one(".corp_name a")
        if not (rec and a):
            continue
        cond = [s.get_text(" ", strip=True) for s in it.select(".job_condition span")]
        loc = cond[0] if cond else ""
        exp = cond[1] if len(cond) > 1 else ""
        lo, hi, newbie = parse_exp(exp)
        date = it.select_one(".job_date .date")
        out.append({
            "source": "saramin",
            "source_id": rec,
            "company": corp.get_text(strip=True) if corp else "",
            "location": re.sub(r"\s+", " ", loc),
            "title": a.get("title") or a.get_text(strip=True),
            "url": f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={rec}",
            "exp_min": lo,
            "exp_max": hi,
            "newbie_only": newbie,
            "due": date.get_text(strip=True) if date else "",
        })
    return out


def parse_exp(text):
    """'경력 5~12년' / '경력2년↑' / '신입' / '신입·경력' / '경력무관' → (min, max, 신입전용)"""
    t = text.replace(" ", "")
    if t == "신입":
        return 0, 0, True
    m = re.search(r"(\d+)~(\d+)년", t)
    if m:
        return int(m.group(1)), int(m.group(2)), False
    m = re.search(r"(\d+)년↑", t)
    if m:
        return int(m.group(1)), None, False
    return None, None, False
