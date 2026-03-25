#!/usr/bin/env python3
"""
AdSense Approval Preparation Script
=====================================
Phase 1: Delete low-quality posts (15) + Sample Page
Phase 2: Create/update 6 unified categories
Phase 3: SEO optimize preserved posts (4) via Rank Math
Phase 4: Rewrite essential pages (5) in Korean
Phase 5: Delete old empty categories
Phase 6: Rebuild navigation menu
"""

import os, sys, json, base64, time, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("adsense_prep")

try:
    import requests
except ImportError:
    log.error("requests 패키지 필요: pip install requests")
    sys.exit(1)

# ── Config ──
WP_URL = os.environ.get("WP_URL", "").rstrip("/")
WP_USER = os.environ.get("WP_USERNAME", "")
WP_PASS = os.environ.get("WP_APP_PASSWORD", "")

if not all([WP_URL, WP_USER, WP_PASS]):
    log.error("환경변수 필요: WP_URL, WP_USERNAME, WP_APP_PASSWORD")
    sys.exit(1)

cred = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {cred}",
    "Content-Type": "application/json",
    "User-Agent": "AutoBlog-AdSensePrep/1.0",
}
API = f"{WP_URL}/wp-json/wp/v2"

def wp_get(endpoint, params=None):
    resp = requests.get(f"{API}/{endpoint}", headers=HEADERS, params=params or {}, timeout=15)
    resp.raise_for_status()
    return resp.json()

def wp_post(endpoint, data):
    resp = requests.post(f"{API}/{endpoint}", headers=HEADERS, json=data, timeout=30)
    return resp

def wp_delete(endpoint):
    resp = requests.delete(f"{API}/{endpoint}?force=true", headers=HEADERS, timeout=15)
    return resp


# ═══════════════════════════════════════════
# Phase 1: Delete low-quality posts + Sample Page
# ═══════════════════════════════════════════

DELETE_POST_IDS = [40, 41, 45, 46, 47, 48, 49, 50, 51, 52, 58, 86, 103, 105, 106]
DELETE_PAGE_IDS = [2]  # Sample Page

def phase1_delete():
    log.info("=" * 60)
    log.info("Phase 1: 저품질 글 15개 + Sample Page 삭제")
    log.info("=" * 60)

    for pid in DELETE_POST_IDS:
        resp = wp_delete(f"posts/{pid}")
        status = "OK" if resp.status_code == 200 else f"ERR({resp.status_code})"
        log.info(f"  Post {pid}: {status}")
        time.sleep(0.3)

    for pid in DELETE_PAGE_IDS:
        resp = wp_delete(f"pages/{pid}")
        status = "OK" if resp.status_code == 200 else f"ERR({resp.status_code})"
        log.info(f"  Page {pid}: {status}")

    log.info(f"  삭제 완료: {len(DELETE_POST_IDS)} posts, {len(DELETE_PAGE_IDS)} pages")


# ═══════════════════════════════════════════
# Phase 2: Create/update 6 unified categories
# ═══════════════════════════════════════════

TARGET_CATEGORIES = [
    {
        "name": "AI 도구 & 생산성",
        "slug": "ai-tools",
        "description": "ChatGPT, Claude, Gemini 등 AI 도구 리뷰, 비교, 활용법과 업무 자동화 팁",
    },
    {
        "name": "재테크 & 투자",
        "slug": "finance-invest",
        "description": "ETF, 적금, 주식, 부동산 등 실전 투자 전략과 재테크 노하우",
    },
    {
        "name": "부업 & 수익화",
        "slug": "side-income",
        "description": "블로그 수익화, 직장인 부업, 프리랜서 수익 다각화 방법",
    },
    {
        "name": "IT & 테크 리뷰",
        "slug": "tech-review",
        "description": "노트북, 스마트 장비, 앱, 소프트웨어 비교 리뷰",
    },
    {
        "name": "정부지원 & 절세",
        "slug": "gov-support",
        "description": "정부 보조금, 지원사업, 종합소득세, 연말정산 절세 가이드",
    },
    {
        "name": "생활 경제",
        "slug": "life-economy",
        "description": "보험 비교, 대출 가이드, 생활비 절약, 전월세 팁",
    },
]

cat_id_map = {}  # slug -> id

def phase2_categories():
    log.info("=" * 60)
    log.info("Phase 2: 카테고리 6개 생성/업데이트")
    log.info("=" * 60)

    for cat in TARGET_CATEGORIES:
        slug = cat["slug"]
        # Check if slug already exists
        existing = wp_get("categories", {"slug": slug})
        if existing:
            cid = existing[0]["id"]
            # Update name/description
            resp = wp_post(f"categories/{cid}", {
                "name": cat["name"],
                "description": cat["description"],
            })
            if resp.status_code == 200:
                cat_id_map[slug] = cid
                log.info(f"  [UPD] {cat['name']} (id={cid})")
            else:
                log.warning(f"  [ERR] {cat['name']} update: {resp.status_code}")
                cat_id_map[slug] = cid  # still usable
        else:
            resp = wp_post("categories", cat)
            if resp.status_code in (200, 201):
                cid = resp.json()["id"]
                cat_id_map[slug] = cid
                log.info(f"  [NEW] {cat['name']} (id={cid})")
            else:
                log.error(f"  [ERR] {cat['name']} create: {resp.status_code} {resp.text[:100]}")

    log.info(f"  카테고리 맵: {cat_id_map}")


# ═══════════════════════════════════════════
# Phase 3: SEO optimize preserved posts
# ═══════════════════════════════════════════

SEO_UPDATES = [
    {
        "post_id": 56,
        "title": "AI 개발자 도구 Descript Gamma Copilot 비교 가이드 2026",
        "slug": "ai-developer-tools-comparison",
        "category_slug": "ai-tools",
        "focus_keyword": "AI 개발자 도구",
        "meta_title": "AI 개발자 도구 비교: Descript vs Gamma vs Copilot (2026) | PlanX AI",
        "meta_desc": "2026년 AI 개발자 필수 도구인 Descript, Gamma, Copilot을 비교합니다. 프로젝트 자동화와 수익화 전략까지 5단계로 상세 분석합니다.",
    },
    {
        "post_id": 57,
        "title": "소상공인 AI 도입 가이드: 엣지AI로 매출 30% 올리는 실전 전략",
        "slug": "edge-ai-guide-small-business",
        "category_slug": "tech-review",
        "focus_keyword": "소상공인 AI 도입",
        "meta_title": "소상공인 AI 도입 가이드: 엣지AI LLM 활용 실전 전략 (2026) | PlanX AI",
        "meta_desc": "소상공인을 위한 엣지AI 도입 가이드입니다. AI 반도체 기반 LLM을 활용해 매출을 30% 증가시키는 실전 전략을 단계별로 알려드립니다.",
    },
    {
        "post_id": 104,
        "title": "개발자 부업 수익화 체크리스트: 코딩 스킬로 월 100만원 만들기",
        "slug": "developer-monetization-checklist",
        "category_slug": "side-income",
        "focus_keyword": "개발자 부업 수익화",
        "meta_title": "개발자 부업 수익화 체크리스트: 5가지 전략으로 30% 수익 높이기 | PlanX AI",
        "meta_desc": "개발자의 코딩 스킬로 부업 수익화하는 방법을 정리했습니다. 주식, 부동산, 적금 등 5가지 전략으로 수익을 높이는 체크리스트를 공개합니다.",
    },
    {
        "post_id": 107,
        "title": "시니어 재테크 전략: 50대 이후 보험 적금 부동산 절세 시너지 활용법",
        "slug": "senior-financial-strategy",
        "category_slug": "finance-invest",
        "focus_keyword": "시니어 재테크",
        "meta_title": "시니어 재테크 전략: 50대 이후 자산 불리기 실전 시너지 | PlanX AI",
        "meta_desc": "50대 이후 시니어를 위한 재테크 전략입니다. 보험, 적금, 부동산, 절세, 연금을 조합해 수익을 30% 증가시키는 실전 시너지 활용법을 소개합니다.",
    },
]

def phase3_seo():
    log.info("=" * 60)
    log.info("Phase 3: 보존 글 4개 SEO 최적화")
    log.info("=" * 60)

    for item in SEO_UPDATES:
        pid = item["post_id"]
        cat_slug = item["category_slug"]
        cat_id = cat_id_map.get(cat_slug)

        update_data = {
            "title": item["title"],
            "slug": item["slug"],
        }
        if cat_id:
            update_data["categories"] = [cat_id]

        # Rank Math SEO meta
        update_data["meta"] = {
            "rank_math_title": item["meta_title"],
            "rank_math_description": item["meta_desc"],
            "rank_math_focus_keyword": item["focus_keyword"],
        }

        resp = wp_post(f"posts/{pid}", update_data)
        if resp.status_code == 200:
            new_slug = resp.json().get("slug", "?")
            log.info(f"  [OK] Post {pid}: slug={new_slug}, keyword='{item['focus_keyword']}'")
        else:
            log.warning(f"  [ERR] Post {pid}: {resp.status_code}")
            # Try without meta (Rank Math may not expose via REST)
            update_data.pop("meta", None)
            resp2 = wp_post(f"posts/{pid}", update_data)
            if resp2.status_code == 200:
                log.info(f"  [OK] Post {pid}: slug updated (meta skipped)")
            else:
                log.error(f"  [FAIL] Post {pid}: {resp2.status_code} {resp2.text[:100]}")

        time.sleep(0.5)


# ═══════════════════════════════════════════
# Phase 4: Rewrite essential pages
# ═══════════════════════════════════════════

PAGE_ABOUT = """
<div class="page-content">

<p>안녕하세요! <strong>PlanX AI</strong>에 오신 것을 환영합니다.</p>

<p>PlanX AI는 <strong>인공지능(AI) 기술</strong>과 <strong>생활 경제 정보</strong>를 쉽고 정확하게 전달하는 블로그입니다. 복잡한 기술 트렌드와 금융 정보를 누구나 이해할 수 있도록 풀어서 제공하는 것이 우리의 목표입니다.</p>

<h2>PlanX AI는 무엇을 다루나요?</h2>

<p>PlanX AI는 다음 6가지 핵심 주제를 다룹니다:</p>

<ul>
<li><strong>AI 도구 &amp; 생산성</strong> &mdash; ChatGPT, Claude, Gemini 등 AI 도구 비교와 활용법, 업무 자동화 팁</li>
<li><strong>재테크 &amp; 투자</strong> &mdash; ETF, 적금, 주식 등 실전 투자 전략과 자산 관리 노하우</li>
<li><strong>부업 &amp; 수익화</strong> &mdash; 직장인과 프리랜서를 위한 부업 추천, 블로그 수익화 방법</li>
<li><strong>IT &amp; 테크 리뷰</strong> &mdash; 노트북, 스마트 장비, 소프트웨어 비교 리뷰</li>
<li><strong>정부지원 &amp; 절세</strong> &mdash; 정부 보조금, 지원사업 안내, 세금 절약 가이드</li>
<li><strong>생활 경제</strong> &mdash; 보험 비교, 대출 가이드, 생활비 절약 실전 팁</li>
</ul>

<h2>콘텐츠 원칙</h2>

<p>PlanX AI의 모든 콘텐츠는 다음 원칙을 따릅니다:</p>

<ol>
<li><strong>정확성</strong> &mdash; 공식 데이터와 신뢰할 수 있는 출처를 기반으로 작성합니다. 통계와 수치는 반드시 출처를 명시합니다.</li>
<li><strong>실용성</strong> &mdash; 이론이 아닌, 바로 적용할 수 있는 실전 정보를 제공합니다. 모든 가이드에는 구체적인 단계별 설명이 포함됩니다.</li>
<li><strong>객관성</strong> &mdash; 특정 제품이나 서비스에 편향되지 않은 공정한 비교를 제공합니다. 장점과 단점을 모두 솔직하게 다룹니다.</li>
<li><strong>접근성</strong> &mdash; 전문 용어를 최소화하고, 쉬운 표현과 비유로 설명합니다. 누구나 이해할 수 있는 콘텐츠를 지향합니다.</li>
</ol>

<h2>운영 투명성</h2>

<p>PlanX AI는 독자에게 유용한 정보를 무료로 제공하며, 다음과 같은 방식으로 사이트를 운영합니다:</p>

<ul>
<li>일부 콘텐츠에는 제휴(어필리에이트) 링크가 포함될 수 있습니다. 이 링크를 통해 구매하셔도 독자에게 <strong>추가 비용은 발생하지 않습니다</strong>.</li>
<li>사이트에 광고가 표시될 수 있으며, 이는 양질의 콘텐츠를 지속적으로 제공하기 위한 운영 비용을 충당하기 위함입니다.</li>
<li>콘텐츠 리서치 및 초안 작성에 AI 도구를 활용하며, 모든 콘텐츠는 편집팀의 검수를 거쳐 정확성과 유용성을 확인한 후 게시됩니다.</li>
</ul>

<p>제휴 관계가 콘텐츠의 객관성에 영향을 미치지 않도록 엄격한 편집 기준을 유지합니다.</p>

<h2>독자 여러분께</h2>

<p>PlanX AI는 여러분의 현명한 선택에 도움이 되는 정보를 꾸준히 제공하겠습니다. 궁금한 점이나 다루었으면 하는 주제가 있다면 언제든 <a href="/contact">문의 페이지</a>를 통해 알려주세요.</p>

<p>방문해 주셔서 감사합니다.</p>

</div>
""".strip()

PAGE_PRIVACY = """
<div class="page-content">

<p><strong>시행일:</strong> 2026년 3월 25일<br>
<strong>최종 수정:</strong> 2026년 3월 25일</p>

<p>PlanX AI(https://planx-ai.com, 이하 &ldquo;본 사이트&rdquo;)는 이용자의 개인정보를 소중히 보호합니다. 본 개인정보처리방침은 본 사이트가 어떤 정보를 수집하고, 어떻게 이용하며, 이용자에게 어떤 권리를 보장하는지 설명합니다.</p>

<h2>1. 수집하는 개인정보</h2>

<h3>1-1. 자동으로 수집되는 정보</h3>
<p>본 사이트 방문 시 다음 정보가 자동으로 수집될 수 있습니다:</p>
<ul>
<li>IP 주소</li>
<li>브라우저 종류 및 버전</li>
<li>운영체제 정보</li>
<li>방문 일시 및 페이지 조회 기록</li>
<li>리퍼러(이전 방문 사이트) 정보</li>
<li>기기 유형(데스크톱, 모바일, 태블릿)</li>
</ul>

<h3>1-2. 이용자가 직접 제공하는 정보</h3>
<p>댓글 작성이나 문의 양식 이용 시 다음 정보를 수집할 수 있습니다:</p>
<ul>
<li>이름(닉네임)</li>
<li>이메일 주소</li>
<li>문의 내용</li>
</ul>

<h2>2. 개인정보의 이용 목적</h2>
<p>수집된 개인정보는 다음 목적으로만 이용됩니다:</p>
<ul>
<li>사이트 이용 통계 분석 및 서비스 개선</li>
<li>이용자 문의에 대한 응답</li>
<li>스팸 방지 및 보안 유지</li>
<li>맞춤형 광고 제공 (제3자 광고 서비스 이용)</li>
</ul>

<h2>3. 쿠키(Cookie) 사용</h2>
<p>본 사이트는 이용자 경험 개선 및 통계 분석을 위해 쿠키를 사용합니다.</p>

<h3>3-1. 필수 쿠키</h3>
<p>사이트의 기본 기능(보안, 접근성 등)을 위해 필요한 쿠키입니다. 이 쿠키 없이는 사이트가 정상적으로 작동하지 않을 수 있습니다.</p>

<h3>3-2. 분석 쿠키 (Google Analytics)</h3>
<p>본 사이트는 Google Analytics를 사용하여 방문자 통계를 수집합니다. Google Analytics는 쿠키를 통해 익명화된 데이터를 수집하며, 개인을 식별하지 않습니다. 자세한 내용은 <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Google 개인정보처리방침</a>을 참고하세요.</p>

<h3>3-3. 광고 쿠키 (Google AdSense)</h3>
<p>본 사이트는 Google AdSense를 통해 광고를 게재할 수 있습니다. Google 및 광고 파트너는 이용자의 관심사에 기반한 광고를 표시하기 위해 쿠키를 사용할 수 있습니다. 이용자는 <a href="https://adssettings.google.com" target="_blank" rel="noopener noreferrer">Google 광고 설정</a>에서 개인 맞춤 광고를 비활성화할 수 있습니다.</p>

<h3>3-4. 쿠키 관리</h3>
<p>대부분의 웹 브라우저는 쿠키를 자동으로 허용하지만, 브라우저 설정을 통해 쿠키를 거부하거나 삭제할 수 있습니다. 단, 쿠키를 거부하면 사이트의 일부 기능이 제한될 수 있습니다.</p>

<h2>4. 개인정보의 보유 및 파기</h2>
<p>수집된 개인정보는 이용 목적이 달성된 후 지체 없이 파기합니다. 단, 관련 법령에 따라 보존이 필요한 경우 해당 기간 동안 보관합니다.</p>
<ul>
<li>방문 기록: 최대 26개월 (Google Analytics 기본 설정)</li>
<li>문의 기록: 응답 완료 후 1년</li>
<li>댓글 데이터: 댓글 삭제 요청 시까지</li>
</ul>

<h2>5. 개인정보의 제3자 제공</h2>
<p>본 사이트는 이용자의 동의 없이 개인정보를 제3자에게 제공하지 않습니다. 단, 다음의 경우는 예외로 합니다:</p>
<ul>
<li>법령에 의해 요구되는 경우</li>
<li>이용자가 사전에 동의한 경우</li>
<li>통계 작성, 학술 연구 등의 목적으로 특정 개인을 식별할 수 없는 형태로 제공하는 경우</li>
</ul>

<h2>6. 이용하는 제3자 서비스</h2>
<p>본 사이트는 다음 제3자 서비스를 이용하며, 각 서비스는 자체 개인정보처리방침에 따라 데이터를 처리합니다:</p>
<ul>
<li><strong>Google Analytics</strong> &mdash; 방문 통계 분석</li>
<li><strong>Google AdSense</strong> &mdash; 광고 게재</li>
<li><strong>쿠팡 파트너스</strong> &mdash; 제휴 마케팅</li>
<li><strong>Cloudflare</strong> &mdash; 보안 및 성능 최적화(CDN)</li>
<li><strong>WordPress.com / Starter</strong> &mdash; 웹 호스팅</li>
</ul>

<h2>7. 이용자의 권리</h2>
<p>이용자는 언제든지 다음 권리를 행사할 수 있습니다:</p>
<ul>
<li>개인정보 열람, 정정, 삭제 요청</li>
<li>개인정보 처리 정지 요청</li>
<li>쿠키 수집 거부 (브라우저 설정을 통해)</li>
<li>마케팅 목적 데이터 이용 거부</li>
</ul>
<p>위 권리 행사를 원하시면 <a href="/contact">문의 페이지</a>를 통해 연락해 주세요. 요청 접수 후 10일 이내에 처리하겠습니다.</p>

<h2>8. 개인정보 보호책임자</h2>
<ul>
<li>사이트명: PlanX AI</li>
<li>웹사이트: https://planx-ai.com</li>
<li>문의: <a href="/contact">문의 페이지</a></li>
</ul>

<h2>9. 아동의 개인정보 보호</h2>
<p>본 사이트는 만 14세 미만 아동의 개인정보를 의도적으로 수집하지 않습니다. 만약 만 14세 미만 아동의 개인정보가 수집된 사실을 알게 되면 즉시 해당 정보를 삭제합니다.</p>

<h2>10. 방침 변경</h2>
<p>본 개인정보처리방침은 법령 변경이나 서비스 변경에 따라 수정될 수 있습니다. 변경 시 본 페이지에 공지하며, 시행일을 명시합니다. 중요한 변경 사항이 있을 경우 사이트 공지사항을 통해 별도로 안내합니다.</p>

</div>
""".strip()

PAGE_CONTACT = """
<div class="page-content">

<p>PlanX AI에 관한 질문, 제안, 협업 제안을 환영합니다.</p>

<h2>이메일 문의</h2>

<p>아래 이메일로 문의해 주시면 영업일 기준 <strong>1~3일 이내</strong>에 답변드리겠습니다.</p>

<p style="font-size: 1.1em; padding: 15px; background: #f8f9fa; border-radius: 8px; display: inline-block;">
&#x1f4e7; <strong>mymiryu@naver.com</strong>
</p>

<h2>문의 유형 안내</h2>

<h3>콘텐츠 관련</h3>
<p>기사 내용의 오류 신고, 정정 요청, 다루었으면 하는 주제 제안 등을 받습니다. 더 정확하고 유용한 콘텐츠를 만드는 데 독자 여러분의 피드백이 큰 도움이 됩니다.</p>

<h3>광고 및 제휴</h3>
<p>광고 게재, 제휴 마케팅, 스폰서십, 제품 리뷰 요청 등 비즈니스 관련 문의를 받습니다. 이메일 제목에 <strong>[광고/제휴]</strong>를 포함해 주시면 빠르게 확인하겠습니다.</p>

<h3>기술 문의</h3>
<p>사이트 이용 중 기술적 문제(페이지 오류, 느린 로딩 등)가 발생하면 사용하신 브라우저와 기기 정보를 함께 알려주세요.</p>

<h3>저작권 및 법적 문의</h3>
<p>저작권 침해 신고, 법적 문의 등은 해당 내용을 구체적으로 기재하여 이메일로 보내주세요.</p>

<h2>유의사항</h2>
<ul>
<li>스팸이나 광고성 메시지는 답변하지 않습니다.</li>
<li>이메일에 주민등록번호, 계좌번호 등 민감한 개인정보를 포함하지 마세요.</li>
<li>문의 내용은 서비스 개선 목적으로만 활용되며, <a href="/privacy-policy">개인정보처리방침</a>에 따라 보호됩니다.</li>
</ul>

<h2>자주 묻는 질문</h2>

<p><strong>Q: 콘텐츠를 인용하거나 공유해도 되나요?</strong><br>
A: 네, 출처(PlanX AI 및 원문 링크)를 명시하시면 자유롭게 인용 가능합니다. 전문 복제는 사전 허가가 필요합니다.</p>

<p><strong>Q: 특정 주제에 대한 글을 요청할 수 있나요?</strong><br>
A: 물론입니다! 이메일로 원하시는 주제를 보내주시면 콘텐츠 기획에 반영하겠습니다.</p>

<p><strong>Q: 제품 리뷰를 요청하려면 어떻게 하나요?</strong><br>
A: 이메일 제목에 [리뷰 요청]을 포함하여 제품 정보와 함께 보내주세요.</p>

</div>
""".strip()

PAGE_DISCLAIMER = """
<div class="page-content">

<p><strong>최종 수정:</strong> 2026년 3월 25일</p>

<p>PlanX AI(https://planx-ai.com, 이하 &ldquo;본 사이트&rdquo;)의 모든 콘텐츠는 정보 제공 목적으로 작성되었습니다. 본 면책조항을 주의 깊게 읽어주세요.</p>

<h2>1. 일반 면책</h2>
<p>본 사이트에 게시된 정보는 일반적인 참고 목적으로만 제공됩니다. 정보의 정확성, 완전성, 적시성을 보장하지 않으며, 이 정보를 기반으로 한 의사결정에 대해 본 사이트는 법적 책임을 지지 않습니다. 중요한 결정을 내리기 전에 반드시 해당 분야 전문가와 상담하시기 바랍니다.</p>

<h2>2. 투자 및 금융 정보 면책</h2>
<p>본 사이트에서 제공하는 재테크, 투자, 금융 관련 정보는 <strong>전문적인 금융 자문이 아닙니다</strong>.</p>
<ul>
<li>주식, ETF, 부동산 등 모든 투자 상품에는 원금 손실 위험이 있습니다.</li>
<li>과거 수익률이 미래 수익을 보장하지 않습니다.</li>
<li>투자 결정을 내리기 전에 반드시 공인된 금융 전문가(투자상담사, 세무사 등)와 상담하시기 바랍니다.</li>
<li>본 사이트의 정보만으로 투자 결정을 내려서 발생한 손실에 대해 본 사이트는 책임을 지지 않습니다.</li>
</ul>

<h2>3. 제휴 링크 공시 (Affiliate Disclosure)</h2>
<p>본 사이트의 일부 링크는 <strong>제휴(어필리에이트) 링크</strong>입니다. 이러한 링크를 통해 제품이나 서비스를 구매하시면, 본 사이트는 소정의 수수료를 받을 수 있습니다.</p>
<p><strong>중요:</strong> 제휴 링크를 통한 구매 시 독자에게 추가 비용이 발생하지 않습니다.</p>

<h3>현재 참여 중인 제휴 프로그램</h3>
<ul>
<li><strong>쿠팡 파트너스</strong> &mdash; &ldquo;이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.&rdquo;</li>
</ul>

<p>제휴 관계는 콘텐츠의 리뷰 평가나 추천 순위에 영향을 미치지 않습니다. 모든 리뷰와 추천은 독립적인 분석과 평가를 기반으로 합니다.</p>

<h2>4. 콘텐츠 정확성</h2>
<p>본 사이트는 정확한 정보를 제공하기 위해 최선을 다하지만, 다음을 보장하지 않습니다:</p>
<ul>
<li>정보의 완전성 또는 최신성</li>
<li>특정 목적에 대한 적합성</li>
<li>제3자 제품 및 서비스의 품질이나 성능</li>
</ul>
<p>제품 가격, 사양, 정책 등은 수시로 변경될 수 있으므로, 구매 전 공식 사이트에서 최신 정보를 확인하시기 바랍니다. 오류를 발견하시면 <a href="/contact">문의 페이지</a>를 통해 알려주세요.</p>

<h2>5. 외부 링크 면책</h2>
<p>본 사이트에는 외부 웹사이트로 연결되는 링크가 포함될 수 있습니다. 외부 사이트의 콘텐츠, 개인정보 처리방침, 운영에 대해 본 사이트는 통제권이 없으며 책임을 지지 않습니다. 외부 링크를 클릭할 때는 해당 사이트의 이용약관과 개인정보처리방침을 확인하시기 바랍니다.</p>

<h2>6. 건강 및 의료 정보 면책</h2>
<p>본 사이트에 게시된 건강 관련 정보는 의학적 조언을 대체하지 않습니다. 건강 문제에 대해서는 반드시 전문 의료인과 상담하시기 바랍니다.</p>

<h2>7. AI 도구 활용 공시</h2>
<p>본 사이트는 콘텐츠 리서치 및 초안 작성 과정에서 AI 도구를 활용할 수 있습니다. 모든 콘텐츠는 편집팀의 검수를 거쳐 정확성과 유용성을 확인한 후 게시됩니다.</p>

<h2>8. 책임 제한</h2>
<p>관련 법률이 허용하는 최대 범위 내에서, 본 사이트 및 운영자는 본 사이트의 이용 또는 이용 불가능으로 인해 발생하는 직접적, 간접적, 우발적, 결과적 손해에 대해 책임을 지지 않습니다.</p>

<h2>9. 면책조항 변경</h2>
<p>본 면책조항은 필요에 따라 수정될 수 있습니다. 변경 시 본 페이지에 공지하며, 최종 수정일을 업데이트합니다.</p>

<h2>10. 문의</h2>
<p>본 면책조항에 관한 질문이 있으시면 <a href="/contact">문의 페이지</a>를 통해 연락해 주세요.</p>

</div>
""".strip()

PAGE_TERMS = """
<div class="page-content">

<p><strong>시행일:</strong> 2026년 3월 25일<br>
<strong>최종 수정:</strong> 2026년 3월 25일</p>

<p>PlanX AI(https://planx-ai.com, 이하 &ldquo;본 사이트&rdquo;)를 이용하시기 전에 본 이용약관을 주의 깊게 읽어주세요. 본 사이트에 접속하거나 이용하는 것은 본 약관에 동의하는 것으로 간주됩니다.</p>

<h2>1. 약관의 적용</h2>
<p>본 약관은 본 사이트의 모든 이용자(이하 &ldquo;이용자&rdquo;)에게 적용됩니다. 본 약관에 동의하지 않는 경우, 사이트 이용을 중단해 주세요.</p>

<h2>2. 서비스 내용</h2>
<p>본 사이트는 AI 기술, 생활 경제, 재테크, 부업 등에 관한 정보성 콘텐츠를 제공합니다. 제공되는 콘텐츠는 일반적인 정보 제공 목적이며, 전문적인 조언(투자, 세무, 의료 등)을 대체하지 않습니다.</p>

<h2>3. 지적재산권</h2>
<p>본 사이트에 게시된 모든 콘텐츠(텍스트, 이미지, 그래픽, 로고, 아이콘 등)는 본 사이트 또는 해당 저작권자의 재산입니다.</p>
<ul>
<li>개인적, 비상업적 목적으로 콘텐츠를 열람하고 인쇄할 수 있습니다.</li>
<li>콘텐츠의 무단 복제, 배포, 수정, 2차 가공, 재게시는 금지됩니다.</li>
<li>콘텐츠를 인용할 경우, 출처(PlanX AI 및 원문 URL)를 반드시 명시해야 합니다.</li>
<li>상업적 목적의 이용은 사전 서면 동의가 필요합니다.</li>
</ul>

<h2>4. 이용자의 의무</h2>
<p>이용자는 다음 행위를 해서는 안 됩니다:</p>
<ul>
<li>불법적이거나 타인의 권리를 침해하는 목적으로 사이트 이용</li>
<li>사이트의 정상적인 운영을 방해하는 행위(DDoS 공격, 과도한 요청 등)</li>
<li>타인의 개인정보를 무단으로 수집하는 행위</li>
<li>스팸, 악성 코드, 바이러스를 유포하는 행위</li>
<li>사이트 콘텐츠를 자동화된 방법(크롤링, 스크래핑, 봇 등)으로 대량 수집하는 행위</li>
<li>본 사이트의 콘텐츠를 자신의 것처럼 게시하는 행위</li>
</ul>

<h2>5. 댓글 정책</h2>
<p>본 사이트에 게시되는 댓글에 대한 책임은 작성자 본인에게 있습니다. 다음에 해당하는 댓글은 사전 통보 없이 삭제될 수 있습니다:</p>
<ul>
<li>욕설, 비방, 혐오 표현이 포함된 댓글</li>
<li>스팸 또는 광고성 댓글</li>
<li>타인의 개인정보가 포함된 댓글</li>
<li>법률을 위반하는 내용의 댓글</li>
</ul>

<h2>6. 면책사항</h2>
<p>본 사이트 이용과 관련된 면책사항은 <a href="/disclaimer">면책조항 페이지</a>를 참고해 주세요.</p>

<h2>7. 링크 정책</h2>
<p>본 사이트로의 링크는 사전 허가 없이 가능합니다. 단, 다음은 금지됩니다:</p>
<ul>
<li>프레임이나 임베드 방식으로 본 사이트의 콘텐츠를 자신의 콘텐츠인 것처럼 표시하는 행위</li>
<li>본 사이트와 제휴나 보증 관계가 있는 것처럼 오인하게 하는 행위</li>
</ul>

<h2>8. 서비스 변경 및 중단</h2>
<p>본 사이트는 사전 통보 없이 콘텐츠를 수정, 삭제하거나 서비스를 일시적 또는 영구적으로 중단할 수 있습니다. 이에 따른 손해에 대해 본 사이트는 책임을 지지 않습니다.</p>

<h2>9. 약관의 변경</h2>
<p>본 약관은 필요에 따라 변경될 수 있습니다. 변경 시 본 페이지에 공지하며, 변경된 약관은 게시 즉시 효력이 발생합니다. 이용자는 정기적으로 본 약관을 확인할 책임이 있습니다.</p>

<h2>10. 준거법 및 관할</h2>
<p>본 약관은 대한민국 법률에 의해 규율되며, 본 약관과 관련된 분쟁은 대한민국 법원의 관할에 따릅니다.</p>

<h2>11. 분리 조항</h2>
<p>본 약관의 일부 조항이 무효 또는 집행 불가능한 것으로 판단되더라도, 나머지 조항은 계속 유효합니다.</p>

<h2>12. 문의</h2>
<p>본 이용약관에 관한 질문이 있으시면 <a href="/contact">문의 페이지</a>를 통해 연락해 주세요.</p>

</div>
""".strip()


PAGE_UPDATES = [
    {"id": 6,  "title": "PlanX AI 소개",        "slug": "about",          "content": PAGE_ABOUT},
    {"id": 3,  "title": "개인정보처리방침",        "slug": "privacy-policy", "content": PAGE_PRIVACY},
    {"id": 11, "title": "문의하기",               "slug": "contact",        "content": PAGE_CONTACT},
    {"id": 15, "title": "면책조항 및 제휴 공시",    "slug": "disclaimer",     "content": PAGE_DISCLAIMER},
    {"id": 18, "title": "이용약관",               "slug": "terms-of-use",   "content": PAGE_TERMS},
]

def phase4_pages():
    log.info("=" * 60)
    log.info("Phase 4: 필수 페이지 5개 재작성")
    log.info("=" * 60)

    for page in PAGE_UPDATES:
        resp = wp_post(f"pages/{page['id']}", {
            "title": page["title"],
            "slug": page["slug"],
            "content": page["content"],
            "status": "publish",
        })
        if resp.status_code == 200:
            new_slug = resp.json().get("slug", "?")
            log.info(f"  [OK] {page['title']} -> /{new_slug}")
        else:
            log.error(f"  [ERR] {page['title']}: {resp.status_code} {resp.text[:100]}")
        time.sleep(0.3)


# ═══════════════════════════════════════════
# Phase 5: Delete old empty categories
# ═══════════════════════════════════════════

KEEP_CAT_SLUGS = {cat["slug"] for cat in TARGET_CATEGORIES}
KEEP_CAT_SLUGS.add("uncategorized")  # WP default, can't delete

def phase5_cleanup_categories():
    log.info("=" * 60)
    log.info("Phase 5: 빈 카테고리 삭제")
    log.info("=" * 60)

    all_cats = wp_get("categories", {"per_page": 100})
    deleted = 0
    for c in all_cats:
        if c["slug"] not in KEEP_CAT_SLUGS:
            resp = wp_delete(f"categories/{c['id']}")
            status = "OK" if resp.status_code == 200 else f"ERR({resp.status_code})"
            log.info(f"  [{status}] {c['name']} (id={c['id']}, count={c['count']})")
            deleted += 1
            time.sleep(0.2)

    log.info(f"  삭제된 카테고리: {deleted}개")


# ═══════════════════════════════════════════
# Phase 6: Rebuild navigation menu
# ═══════════════════════════════════════════

def phase6_menu():
    log.info("=" * 60)
    log.info("Phase 6: 네비게이션 메뉴 재구성")
    log.info("=" * 60)

    # Find menu
    try:
        menus = wp_get("menus")
    except Exception:
        log.warning("  메뉴 API 접근 불가 (테마 미지원 가능). setup_menu.py를 별도 실행하세요.")
        return

    menu_id = None
    for m in menus:
        if "main" in m["name"].lower() or "primary" in m["name"].lower() or menu_id is None:
            menu_id = m["id"]

    if not menu_id:
        log.warning("  메뉴를 찾을 수 없습니다.")
        return

    log.info(f"  메뉴 ID: {menu_id}")

    # Delete old menu items
    try:
        old_items = wp_get("menu-items", {"menus": menu_id, "per_page": 100})
        for item in old_items:
            wp_delete(f"menu-items/{item['id']}")
        log.info(f"  기존 메뉴 아이템 {len(old_items)}개 삭제")
    except Exception as e:
        log.warning(f"  메뉴 아이템 삭제 실패: {e}")

    # Create new menu items
    order = 1

    # Home
    resp = wp_post("menu-items", {
        "title": "홈",
        "url": WP_URL + "/",
        "status": "publish",
        "menus": menu_id,
        "type": "custom",
        "menu_order": order,
    })
    log.info(f"  [{'OK' if resp.status_code in (200, 201) else 'ERR'}] 홈 (order={order})")
    order += 1

    # Category items
    for cat in TARGET_CATEGORIES:
        slug = cat["slug"]
        cid = cat_id_map.get(slug)
        if not cid:
            continue

        item_data = {
            "title": cat["name"],
            "status": "publish",
            "menus": menu_id,
            "type": "taxonomy",
            "object": "category",
            "object_id": cid,
            "menu_order": order,
        }
        resp = wp_post("menu-items", item_data)

        if resp.status_code not in (200, 201):
            # Fallback to custom link
            item_data = {
                "title": cat["name"],
                "url": f"{WP_URL}/category/{slug}/",
                "status": "publish",
                "menus": menu_id,
                "type": "custom",
                "menu_order": order,
            }
            resp = wp_post("menu-items", item_data)

        log.info(f"  [{'OK' if resp.status_code in (200, 201) else 'ERR'}] {cat['name']} (order={order})")
        order += 1

    # Essential page links
    essential_pages = [
        {"title": "소개", "url": f"{WP_URL}/about/"},
        {"title": "문의", "url": f"{WP_URL}/contact/"},
    ]
    for pg in essential_pages:
        resp = wp_post("menu-items", {
            "title": pg["title"],
            "url": pg["url"],
            "status": "publish",
            "menus": menu_id,
            "type": "custom",
            "menu_order": order,
        })
        log.info(f"  [{'OK' if resp.status_code in (200, 201) else 'ERR'}] {pg['title']} (order={order})")
        order += 1

    log.info(f"  메뉴 재구성 완료: {order - 1}개 아이템")


# ═══════════════════════════════════════════
# Final verification
# ═══════════════════════════════════════════

def verify():
    log.info("=" * 60)
    log.info("최종 확인")
    log.info("=" * 60)

    posts = wp_get("posts", {"per_page": 50, "_fields": "id,title,slug,categories,status"})
    log.info(f"  남은 글: {len(posts)}개")
    for p in posts:
        log.info(f"    [{p['id']}] {p['title']['rendered'][:50]} | slug={p['slug'][:40]} | cats={p['categories']}")

    pages = wp_get("pages", {"per_page": 50, "_fields": "id,title,slug,status"})
    log.info(f"  페이지: {len(pages)}개")
    for p in pages:
        log.info(f"    [{p['id']}] {p['title']['rendered'][:40]} | /{p['slug']}")

    cats = wp_get("categories", {"per_page": 50, "_fields": "id,name,slug,count"})
    log.info(f"  카테고리: {len(cats)}개")
    for c in cats:
        log.info(f"    [{c['id']}] {c['name']} ({c['slug']}) - {c['count']}개 글")


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

def main():
    log.info("AdSense Approval Preparation - 시작")
    log.info(f"Target: {WP_URL}")
    log.info("")

    phase1_delete()
    phase2_categories()
    phase3_seo()
    phase4_pages()
    phase5_cleanup_categories()
    phase6_menu()
    verify()

    log.info("")
    log.info("=" * 60)
    log.info("모든 Phase 완료!")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
