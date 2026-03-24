#!/usr/bin/env python3
"""
WordPress 카테고리 생성 + 네비게이션 메뉴 설정
GitHub Actions 또는 로컬에서 실행 (WP 인증 환경변수 필요)
"""
import os, json, sys, base64

WP_URL = os.environ.get("WP_URL", "").rstrip("/")
WP_USER = os.environ.get("WP_USERNAME", "")
WP_PASS = os.environ.get("WP_APP_PASSWORD", "")

if not all([WP_URL, WP_USER, WP_PASS]):
    print("ERROR: WP_URL, WP_USERNAME, WP_APP_PASSWORD 환경변수 필요")
    sys.exit(1)

import requests

cred = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {cred}",
    "Content-Type": "application/json",
    "User-Agent": "AutoBlog/1.0",
}
API = f"{WP_URL}/wp-json/wp/v2"

# ── 1. 카테고리 생성 ──
TARGET_CATEGORIES = [
    {"name": "AI 도구 & 활용", "slug": "ai-tools", "description": "AI 도구 리뷰, 활용법, 자동화 팁"},
    {"name": "정부지원 & 혜택", "slug": "gov-support", "description": "정부 보조금, 지원금, 숨은 혜택 정보"},
    {"name": "행사 & 컨퍼런스", "slug": "events", "description": "IT, 비즈니스, 산업별 행사 및 컨퍼런스"},
    {"name": "핫 뉴스", "slug": "hot-news", "description": "지금 알아야 할 핫한 뉴스와 트렌드"},
    {"name": "재테크 & 투자", "slug": "finance", "description": "돈 버는 법, 절세, 투자 전략, 부동산"},
    {"name": "교육 & 생산성", "slug": "education", "description": "자기계발, 생산성 도구, 온라인 교육"},
]

print("=== 카테고리 생성 ===")
cat_ids = {}
for cat in TARGET_CATEGORIES:
    # 이미 존재하는지 확인
    resp = requests.get(f"{API}/categories", params={"slug": cat["slug"]}, headers=HEADERS, timeout=10)
    existing = resp.json()
    if existing and len(existing) > 0:
        cat_ids[cat["slug"]] = existing[0]["id"]
        print(f"  [EXISTS] {cat['name']} (id={existing[0]['id']})")
    else:
        resp = requests.post(f"{API}/categories", headers=HEADERS, json=cat, timeout=10)
        if resp.status_code == 201:
            cat_ids[cat["slug"]] = resp.json()["id"]
            print(f"  [CREATED] {cat['name']} (id={resp.json()['id']})")
        else:
            print(f"  [ERROR] {cat['name']}: {resp.status_code} {resp.text[:200]}")

# ── 2. 네비게이션 메뉴 설정 ──
print("\n=== 메뉴 설정 ===")

# 기존 메뉴 확인 (WP REST API v2 + nav_menu)
menu_resp = requests.get(
    f"{WP_URL}/wp-json/wp/v2/navigation",
    headers=HEADERS, timeout=10
)

# 메뉴 항목 구성 (홈 + 6개 카테고리)
MENU_ITEMS = [
    {"title": "홈", "url": WP_URL, "type": "custom"},
]
for cat in TARGET_CATEGORIES:
    if cat["slug"] in cat_ids:
        MENU_ITEMS.append({
            "title": cat["name"],
            "url": f"{WP_URL}/category/{cat['slug']}/",
            "type": "category",
            "cat_id": cat_ids[cat["slug"]],
        })

# WP 메뉴는 REST API로 직접 관리가 제한적이므로,
# wp_nav_menu를 위한 메뉴 아이템을 생성하는 대안 접근

# 먼저 기존 메뉴 확인
menus_resp = requests.get(
    f"{WP_URL}/wp-json/wp/v2/menu-items",
    headers=HEADERS, timeout=10
)

if menus_resp.status_code == 200:
    existing_items = menus_resp.json()
    print(f"  기존 메뉴 아이템: {len(existing_items)}개")
else:
    print(f"  메뉴 API 상태: {menus_resp.status_code}")
    existing_items = []

# 메뉴 위치에 할당된 메뉴 확인
locations_resp = requests.get(
    f"{WP_URL}/wp-json/wp/v2/menu-locations",
    headers=HEADERS, timeout=10
)
if locations_resp.status_code == 200:
    locations = locations_resp.json()
    print(f"  메뉴 위치: {json.dumps(locations, ensure_ascii=False)[:300]}")
else:
    print(f"  메뉴 위치 API: {locations_resp.status_code}")

# 기존 nav menus (termbased) 확인
nav_menus = requests.get(
    f"{WP_URL}/wp-json/wp/v2/menus",
    headers=HEADERS, timeout=10
)
if nav_menus.status_code == 200:
    for menu in nav_menus.json():
        print(f"  메뉴: [{menu.get('id')}] {menu.get('name', '?')}")
else:
    print(f"  메뉴 조회: {nav_menus.status_code}")

# ── 3. 기존 카테고리 정리 (옵션) ──
print("\n=== 기존 카테고리 현황 ===")
all_cats = requests.get(f"{API}/categories", params={"per_page": 50}, headers=HEADERS, timeout=10).json()
for c in all_cats:
    marker = " ★" if c["slug"] in cat_ids else ""
    print(f"  [{c['id']:>3}] {c['name']:20s} ({c['count']}편){marker}")

print(f"\n카테고리 {len(cat_ids)}개 준비 완료.")
print("메뉴 설정은 WP Admin > 외모 > 메뉴에서 직접 설정하거나,")
print("아래 스크립트로 자동 설정할 수 있습니다.")

# ── 4. 페이지 기반 메뉴 아이템 (필수 페이지) ──
print("\n=== 필수 페이지 확인 ===")
pages_resp = requests.get(
    f"{API}/pages", params={"per_page": 50, "_fields": "id,title,slug,status"},
    headers=HEADERS, timeout=10
)
if pages_resp.status_code == 200:
    pages = pages_resp.json()
    for p in pages:
        print(f"  [{p['id']:>3}] {p['title']['rendered']:30s} (/{p['slug']}/)")

print("\n완료!")
