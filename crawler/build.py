"""
전체 실행 파일:  python3 crawler/build.py

1) 4개 사이트에서 공고 수집  →  2) 직군·지역 필터  →  3) 중복 제거
4) 잡플래닛 평점 붙이기  →  5) 적합도 점수  →  6) site/jobs.json 저장
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from common import (classify, exp_text, norm_company, norm_title,  # noqa: E402
                    region_ok, score, short_location)
from sources import jobkorea, jobplanet, remember, saramin, wanted  # noqa: E402

KST = timezone(timedelta(hours=9))
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "site", "jobs.json")
SOURCES = {"wanted": wanted, "jobkorea": jobkorea, "saramin": saramin, "remember": remember}


def collect():
    raw, status = [], {}
    for name, mod in SOURCES.items():
        print(f"▶ {name} 수집 중…")
        try:
            rows = mod.fetch()
            raw += rows
            status[name] = {"ok": True, "raw": len(rows)}
            print(f"   {len(rows)}건")
        except Exception as e:  # 한 사이트가 막혀도 나머지는 계속
            status[name] = {"ok": False, "raw": 0, "error": str(e)[:200]}
            print(f"   실패: {e}")
    return raw, status


def refine(raw):
    """직군/지역 필터 + 사이트 간 중복 제거."""
    merged = {}
    for j in raw:
        j["tier"] = classify(j["title"])
        if not j["tier"] or not region_ok(j["location"]):
            continue
        j["location"] = short_location(j["location"])
        key = norm_company(j["company"]) + "|" + norm_title(j["title"])
        if key in merged:
            m = merged[key]
            if j["source"] not in m["sources"]:
                m["sources"].append(j["source"])
                m["links"][j["source"]] = j["url"]
            continue
        j["sources"] = [j["source"]]
        j["links"] = {j["source"]: j["url"]}
        merged[key] = j
    return list(merged.values())


def add_ratings(jobs):
    cache = jobplanet.load_cache()
    names = sorted({j["company"] for j in jobs if not j.get("headhunter")})
    print(f"▶ 잡플래닛 평점 확인: 회사 {len(names)}곳 (캐시 {len(cache)}곳)")
    found = {}
    for n in names:
        found[n] = jobplanet.lookup(n, cache)
    jobplanet.save_cache(cache)
    st = jobplanet.STATE
    print(f"   새로 조회 {st['new_lookups']}곳" + (" · 잡플래닛 차단으로 중간에 멈춤" if st["blocked"] else ""))
    for j in jobs:
        hit = None if j.get("headhunter") else found.get(j["company"])
        j["rating"] = hit.get("rating") if hit else None
        j["review_count"] = hit.get("count") if hit else None
        j["jobplanet_url"] = f'https://www.jobplanet.co.kr/companies/{hit["id"]}' if hit else None


def load_previous():
    try:
        with open(OUT, encoding="utf-8") as f:
            prev = json.load(f)
        return {j["key"]: j.get("first_seen") for j in prev.get("jobs", [])}
    except (OSError, ValueError, KeyError):
        return {}


def main():
    now = datetime.now(KST)
    raw, status = collect()
    jobs = refine(raw)
    add_ratings(jobs)

    prev = load_previous()
    today = now.strftime("%Y-%m-%d")
    out = []
    for j in jobs:
        score(j)
        key = norm_company(j["company"]) + "|" + norm_title(j["title"])
        out.append({
            "key": key,
            "tier": j["tier"],
            "score": j["score"],
            "reasons": j["reasons"],
            "company": j["company"],
            "headhunter": bool(j.get("headhunter")),
            "location": j["location"],
            "rating": j["rating"],
            "review_count": j.get("review_count"),
            "jobplanet_url": j["jobplanet_url"],
            "title": j["title"],
            "url": j["url"],
            "links": j["links"],
            "sources": j["sources"],
            "experience": exp_text(j.get("exp_min"), j.get("exp_max"), j.get("newbie_only")),
            "due": j.get("due", ""),
            "first_seen": prev.get(key) or today,
        })
    out.sort(key=lambda x: (-x["score"], -(x["rating"] or 0)))

    for name in status:
        status[name]["kept"] = sum(1 for j in out if name in j["sources"])

    # 사이트 하나가 실패하면 직전 데이터에서 그 사이트 공고를 살려 둡니다.
    failed = [n for n, s in status.items() if not s["ok"]]
    if failed and os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f).get("jobs", [])
        have = {j["key"] for j in out}
        carry = [j for j in old if j["key"] not in have and set(j["sources"]) & set(failed)]
        out += carry
        print(f"▶ 실패한 사이트({', '.join(failed)})는 직전 공고 {len(carry)}건 유지")

    data = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
        "sources": status,
        "total": len(out),
        # 첫 수집이면 전부 '새 공고'가 되므로 0으로 둡니다.
        "new_today": sum(1 for j in out if j["first_seen"] == today) if prev else 0,
        "jobs": out,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"✔ 완료: {len(out)}건 → site/jobs.json  ({data['updated_at']})")


if __name__ == "__main__":
    main()
