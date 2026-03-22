#!/usr/bin/env python3
"""
AutoBlog Engine v5.0 — Cloudways WordPress 자동 발행 엔진
=========================================================
키워드 선택 → AI 글 생성 (DeepSeek+Claude) → 이미지 삽입 → 
제휴 링크 삽입 → WordPress 발행 → SNS 공유 → Supabase 로깅

사용: python scripts/main.py [--dry-run] [--count 5] [--pipeline autoblog]
"""

import os, sys, json, time, random, hashlib, logging, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 경로 설정 ──
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# ── 로깅 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("autoblog")

# ── 환경변수 ──
WP_URL = os.environ.get("WP_URL", "")
WP_USER = os.environ.get("WP_USERNAME", "")
WP_PASS = os.environ.get("WP_APP_PASSWORD", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
CLAUDE_KEY = os.environ.get("CLAUDE_API_KEY", "")
UNSPLASH_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SITE_ID = os.environ.get("SITE_ID", "site-1")

KST = timezone(timedelta(hours=9))


# ═══════════════════════════════════════════════════════
# 1. 키워드 관리
# ═══════════════════════════════════════════════════════
class KeywordManager:
    def __init__(self):
        self.kw_file = DATA / "keywords.json"
        self.used_file = DATA / "used_keywords.json"
        self.keywords = self._load(self.kw_file, {"keywords": []})
        self.used = self._load(self.used_file, [])

    def _load(self, path, default):
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    def _save_used(self):
        with open(self.used_file, "w", encoding="utf-8") as f:
            json.dump(self.used, f, ensure_ascii=False, indent=2)

    def select(self, count=5, pipeline="autoblog"):
        """미사용 키워드 중 count개 선택"""
        pool = self.keywords.get("keywords", [])
        available = [
            kw for kw in pool
            if kw.get("keyword") not in self.used
            and kw.get("pipeline", "autoblog") == pipeline
        ]

        if len(available) < count:
            log.warning(f"가용 키워드 {len(available)}개 (요청 {count}개)")
            count = len(available)

        # 타입별 비율: traffic 60%, conversion 30%, high_cpa 10%
        selected = []
        by_type = {}
        for kw in available:
            t = kw.get("type", "traffic")
            by_type.setdefault(t, []).append(kw)

        targets = {"traffic": max(1, int(count * 0.6)),
                   "conversion": max(1, int(count * 0.3)),
                   "high_cpa": max(0, count - max(1, int(count * 0.6)) - max(1, int(count * 0.3)))}

        for ktype, num in targets.items():
            pool_type = by_type.get(ktype, [])
            random.shuffle(pool_type)
            selected.extend(pool_type[:num])

        # 부족하면 나머지에서 채움
        if len(selected) < count:
            remaining = [kw for kw in available if kw not in selected]
            random.shuffle(remaining)
            selected.extend(remaining[:count - len(selected)])

        return selected[:count]

    def mark_used(self, keyword):
        if keyword not in self.used:
            self.used.append(keyword)
            self._save_used()


# ═══════════════════════════════════════════════════════
# 2. AI 글 생성 — 멀티모델 라우팅
# 우선순위: Grok → Gemini → DeepSeek (초안)
# 폴리싱: Claude Sonnet (품질 극대화)
# ═══════════════════════════════════════════════════════
GROK_KEY = os.environ.get("GROK_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

# 프롬프트 (공용)
DRAFT_PROMPT = """당신은 한국 최고의 금융·실용정보 블로거입니다.
10년 경력의 전문 필진처럼 깊이 있고 실용적인 글을 씁니다.

키워드: {keyword}
검색의도: {intent}
카테고리: {category}

작성 규칙:
1. 제목: 호기심+구체성 (숫자, 비교, 의문문 활용). <title> 태그로 감싸기
2. 도입부: 3문장, 독자 고민을 정확히 짚고 "이 글을 읽으면 ~를 알 수 있다" 약속
3. 본문: H2 소제목 4~6개, 각 300~500자
   - 구체적 수치·비교표·실제 사례 필수 (숫자 없는 문단 금지)
   - "~입니다", "~한 것입니다" 같은 딱딱한 종결 금지 → 대화체
   - 핵심 포인트는 <strong> 강조
4. 마무리: 3줄 요약 + 구체적 행동 유도 (CTA)
5. 톤: 친근하되 전문적, "여러분" 호칭, 이모지 자제
6. 분량: 4,000~7,000자 (충분히 상세하게)

HTML 형식 (제목 <h1> 제외, 본문만). <title>글제목</title>을 콘텐츠 최상단에.
"""

POLISH_PROMPT = """아래 블로그 초안을 프리미엄 품질로 업그레이드하세요.

키워드: {keyword}

업그레이드 규칙:
1. AI 특유 표현 완전 제거: "다양한", "중요합니다", "살펴보겠습니다", "알아보겠습니다"
   → 자연스러운 구어체로 100% 교체
2. 모든 문단에 최소 1개 구체적 수치/사례/비교 추가
3. 문장 길이 변주: 짧은 문장(5어절)과 긴 문장(15어절) 혼합
4. 읽는 리듬감: 질문→답변, 문제→해결, 비교→추천 패턴
5. SEO: 키워드를 H2, 도입부, 마무리에 자연스럽게 포함
6. HTML 구조 100% 유지, 내용만 퀄리티업

초안:
{draft}
"""


class ContentGenerator:
    """멀티모델 AI 글 생성기 — Grok→Gemini→DeepSeek (초안) + Claude (폴리싱)"""

    COST_RATES = {
        "grok-3-mini": {"input": 0.0003, "output": 0.0005},
        "grok-3": {"input": 0.003, "output": 0.015},
        "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
        "gemini-2.5-flash-preview-05-20": {"input": 0.00015, "output": 0.0006},
        "deepseek-chat": {"input": 0.00014, "output": 0.00028},
        "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
        "claude-haiku-4-5-20241022": {"input": 0.001, "output": 0.005},
    }

    def generate(self, keyword, intent="informational", category=""):
        """멀티모델 폴체인: Grok→Gemini→DeepSeek (초안) + Claude (폴리싱)"""
        prompt = DRAFT_PROMPT.format(keyword=keyword, intent=intent, category=category)

        # ── Step 1: 초안 생성 (폴백 체인) ──
        draft = None
        draft_model = None

        # 1차: Grok
        if GROK_KEY:
            draft, draft_model = self._call_grok(prompt)

        # 2차: Gemini
        if not draft and GEMINI_KEY:
            draft, draft_model = self._call_gemini(prompt)

        # 3차: DeepSeek (백업)
        if not draft and DEEPSEEK_KEY:
            draft, draft_model = self._call_deepseek(prompt)

        if not draft:
            log.error(f"❌ 모든 모델 실패: {keyword}")
            return None, 0, 0

        log.info(f"✅ 초안 완료 [{draft_model}] ({len(draft)}자)")
        draft_cost = self._estimate_cost(draft_model, prompt, draft)

        # ── Step 2: Claude 폴리싱 (품질 극대화) ──
        if CLAUDE_KEY:
            polish_prompt = POLISH_PROMPT.format(keyword=keyword, draft=draft)
            polished = self._call_claude_polish(polish_prompt)
            if polished:
                polish_cost = self._estimate_cost("claude-sonnet-4-20250514", polish_prompt, polished)
                log.info(f"✨ 폴리싱 완료 [Claude Sonnet] ({len(polished)}자)")
                return polished, draft_cost + polish_cost, len(polished)

        return draft, draft_cost, len(draft)

    # ── Grok (xAI) ──
    def _call_grok(self, prompt):
        import requests
        try:
            log.info("🤖 Grok 초안 생성 중...")
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROK_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-3-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 5000
                },
                timeout=180
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            self._log_cost("grok-3-mini", "xai", "content",
                          usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
            return content, "grok-3-mini"
        except Exception as e:
            log.warning(f"⚠️ Grok 실패: {e}")
            return None, None

    # ── Gemini (Google) ──
    def _call_gemini(self, prompt):
        import requests
        try:
            log.info("🤖 Gemini 초안 생성 중...")
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.8,
                        "maxOutputTokens": 5000
                    }
                },
                timeout=180
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            self._log_cost("gemini-2.0-flash", "google", "content",
                          usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0))
            return content, "gemini-2.0-flash"
        except Exception as e:
            log.warning(f"⚠️ Gemini 실패: {e}")
            return None, None

    # ── DeepSeek (백업) ──
    def _call_deepseek(self, prompt):
        import requests
        try:
            log.info("🤖 DeepSeek 초안 생성 중 (백업)...")
            resp = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 5000
                },
                timeout=180
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            self._log_cost("deepseek-chat", "deepseek", "content",
                          usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
            return content, "deepseek-chat"
        except Exception as e:
            log.warning(f"⚠️ DeepSeek 실패: {e}")
            return None, None

    # ── Claude 폴리싱 (Sonnet — 최고 품질) ──
    def _call_claude_polish(self, prompt):
        import requests
        try:
            log.info("✨ Claude Sonnet 폴리싱 중...")
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 6000,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=180
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            usage = data.get("usage", {})
            self._log_cost("claude-sonnet-4-20250514", "anthropic", "polish",
                          usage.get("input_tokens", 0), usage.get("output_tokens", 0))
            return content
        except Exception as e:
            log.warning(f"⚠️ Claude 폴리싱 실패 (초안 그대로 사용): {e}")
            return None

    # ── 비용 계산 ──
    def _estimate_cost(self, model, prompt_text, output_text):
        input_t = len(prompt_text) // 4
        output_t = len(output_text) // 4
        r = self.COST_RATES.get(model, {"input": 0.001, "output": 0.002})
        return (input_t / 1000 * r["input"]) + (output_t / 1000 * r["output"])

    def _log_cost(self, model, provider, purpose, input_t, output_t):
        r = self.COST_RATES.get(model, {"input": 0.001, "output": 0.002})
        cost_usd = (input_t / 1000 * r["input"]) + (output_t / 1000 * r["output"])
        cost_krw = int(cost_usd * 1450)
        log.info(f"💰 {model}: {input_t}+{output_t} tokens = ${cost_usd:.4f} (₩{cost_krw})")

        if SUPABASE_URL and SUPABASE_KEY:
            try:
                import requests
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/api_costs",
                    headers={
                        "apikey": SUPABASE_KEY,
                        "Authorization": f"Bearer {SUPABASE_KEY}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    },
                    json={
                        "site_id": SITE_ID,
                        "model": model,
                        "provider": provider,
                        "purpose": purpose,
                        "tokens_input": input_t,
                        "tokens_output": output_t,
                        "cost_usd": round(cost_usd, 6),
                        "cost_krw": cost_krw,
                        "pipeline": "autoblog"
                    },
                    timeout=10
                )
            except Exception:
                pass


# ═══════════════════════════════════════════════════════
# 3. 이미지 삽입
# ═══════════════════════════════════════════════════════
class ImageManager:
    def fetch_image(self, keyword):
        """Unsplash에서 키워드 관련 이미지 URL 가져오기"""
        if not UNSPLASH_KEY:
            return None

        import requests
        try:
            resp = requests.get(
                "https://api.unsplash.com/search/photos",
                headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
                params={"query": keyword, "per_page": 3, "orientation": "landscape"},
                timeout=10
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                img = random.choice(results[:3])
                return {
                    "url": img["urls"]["regular"],
                    "alt": img.get("alt_description", keyword),
                    "credit": img["user"]["name"],
                    "link": img["user"]["links"]["html"]
                }
        except Exception as e:
            log.warning(f"Unsplash 이미지 실패: {e}")
        return None

    def insert_image(self, content, image_data):
        """콘텐츠 첫 번째 H2 앞에 이미지 삽입"""
        if not image_data:
            return content, False

        img_html = (
            f'<figure style="margin:20px 0">'
            f'<img src="{image_data["url"]}" alt="{image_data["alt"]}" '
            f'style="width:100%;border-radius:8px;" loading="lazy"/>'
            f'<figcaption style="text-align:center;font-size:12px;color:#888;margin-top:8px;">'
            f'Photo by <a href="{image_data["link"]}?utm_source=autoblog" target="_blank">'
            f'{image_data["credit"]}</a> on Unsplash</figcaption>'
            f'</figure>'
        )

        # 첫 번째 <h2> 앞에 삽입
        if "<h2" in content:
            idx = content.index("<h2")
            return content[:idx] + img_html + content[idx:], True
        else:
            return img_html + content, True


# ═══════════════════════════════════════════════════════
# 4. 제휴 링크 삽입
# ═══════════════════════════════════════════════════════
class AffiliateManager:
    def __init__(self):
        self.links_file = DATA / "affiliates.json"
        self.links = self._load()

    def _load(self):
        if self.links_file.exists():
            with open(self.links_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"coupang": {}, "cpa": {}, "adsense_slots": []}

    def insert_links(self, content, keyword, category):
        """키워드/카테고리에 맞는 제휴 링크 삽입"""
        # 쿠팡 파트너스 링크
        coupang = self.links.get("coupang", {})
        matched_links = []
        
        for cat, links in coupang.items():
            if cat.lower() in keyword.lower() or cat.lower() in category.lower():
                if isinstance(links, list):
                    matched_links.extend(links)
                elif isinstance(links, str):
                    matched_links.append({"name": cat, "url": links})

        if matched_links:
            link_html = self._build_product_box(matched_links[:3])
            # 마지막 H2 섹션 뒤에 삽입
            if "</h2>" in content:
                parts = content.rsplit("</h2>", 1)
                content = parts[0] + "</h2>" + link_html + parts[1]
            else:
                content += link_html

        return content, bool(matched_links)

    def _build_product_box(self, links):
        """쿠팡 상품 추천 박스 HTML"""
        items = ""
        for link in links:
            name = link.get("name", "추천 상품")
            url = link.get("url", "#")
            if "YOUR_" in url:
                continue
            items += (
                f'<li style="margin:8px 0">'
                f'<a href="{url}" target="_blank" rel="nofollow sponsored" '
                f'style="color:#1a73e8;text-decoration:none;font-weight:600">'
                f'👉 {name} 최저가 확인하기</a></li>'
            )

        if not items:
            return ""

        return (
            f'\n<div style="background:#f8f9ff;border:2px solid #dde3ff;'
            f'border-radius:12px;padding:20px;margin:24px 0">'
            f'<p style="font-weight:700;font-size:16px;margin:0 0 12px">🛒 추천 상품</p>'
            f'<ul style="list-style:none;padding:0;margin:0">{items}</ul>'
            f'<p style="font-size:11px;color:#999;margin:12px 0 0">'
            f'이 포스팅은 쿠팡 파트너스 활동의 일환으로, 일정액의 수수료를 제공받을 수 있습니다.</p>'
            f'</div>\n'
        )


# ═══════════════════════════════════════════════════════
# 5. WordPress 발행
# ═══════════════════════════════════════════════════════
class WordPressPublisher:
    def __init__(self):
        import base64
        self.url = WP_URL.rstrip("/")
        cred = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/json"
        }

    def publish(self, title, content, category="", tags=None):
        """WordPress REST API로 글 발행"""
        import requests

        # 카테고리 ID 가져오기/생성
        cat_id = self._get_or_create_category(category) if category else None

        post_data = {
            "title": title,
            "content": content,
            "status": "publish",
            "format": "standard",
        }
        if cat_id:
            post_data["categories"] = [cat_id]
        if tags:
            tag_ids = [self._get_or_create_tag(t) for t in tags[:5]]
            post_data["tags"] = [t for t in tag_ids if t]

        try:
            resp = requests.post(
                f"{self.url}/wp-json/wp/v2/posts",
                headers=self.headers,
                json=post_data,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "id": data["id"],
                "url": data.get("link", ""),
                "title": data.get("title", {}).get("rendered", title),
                "status": "published"
            }
        except Exception as e:
            log.error(f"❌ 발행 실패: {e}")
            return {"status": "failed", "error": str(e)}

    def _get_or_create_category(self, name):
        import requests
        try:
            resp = requests.get(
                f"{self.url}/wp-json/wp/v2/categories",
                headers=self.headers,
                params={"search": name, "per_page": 5},
                timeout=10
            )
            cats = resp.json()
            for c in cats:
                if c["name"].lower() == name.lower():
                    return c["id"]

            # 생성
            resp = requests.post(
                f"{self.url}/wp-json/wp/v2/categories",
                headers=self.headers,
                json={"name": name},
                timeout=10
            )
            return resp.json().get("id")
        except Exception:
            return None

    def _get_or_create_tag(self, name):
        import requests
        try:
            resp = requests.get(
                f"{self.url}/wp-json/wp/v2/tags",
                headers=self.headers,
                params={"search": name, "per_page": 5},
                timeout=10
            )
            tags = resp.json()
            for t in tags:
                if t["name"].lower() == name.lower():
                    return t["id"]

            resp = requests.post(
                f"{self.url}/wp-json/wp/v2/tags",
                headers=self.headers,
                json={"name": name},
                timeout=10
            )
            return resp.json().get("id")
        except Exception:
            return None


# ═══════════════════════════════════════════════════════
# 6. Supabase 로깅
# ═══════════════════════════════════════════════════════
class SupabaseLogger:
    def __init__(self):
        self.url = SUPABASE_URL
        self.key = SUPABASE_KEY
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

    def log_publish(self, data):
        if not self.url or not self.key:
            return
        import requests
        try:
            record = {
                "site_id": SITE_ID,
                "title": data.get("title", ""),
                "url": data.get("url", ""),
                "keyword": data.get("keyword", ""),
                "intent": data.get("intent", ""),
                "category": data.get("category", ""),
                "pipeline": data.get("pipeline", "autoblog"),
                "content_length": data.get("content_length", 0),
                "has_image": data.get("has_image", False),
                "has_coupang": data.get("has_coupang", False),
                "status": data.get("status", "published"),
                "error_message": data.get("error_message", ""),
                "published_at": datetime.now(KST).isoformat(),
            }
            requests.post(
                f"{self.url}/rest/v1/publish_logs",
                headers=self.headers,
                json=record,
                timeout=10
            )
            log.info(f"📊 Supabase 로그 기록: {data.get('title', '')[:30]}")
        except Exception as e:
            log.warning(f"Supabase 로깅 실패: {e}")

    def log_alert(self, title, message, severity="warning", alert_type="info"):
        if not self.url or not self.key:
            return
        import requests
        try:
            requests.post(
                f"{self.url}/rest/v1/alerts",
                headers=self.headers,
                json={
                    "site_id": SITE_ID,
                    "alert_type": alert_type,
                    "severity": severity,
                    "title": title,
                    "message": message
                },
                timeout=10
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════
# 7. 메인 파이프라인
# ═══════════════════════════════════════════════════════
def extract_title(content):
    """HTML에서 <title> 태그 추출"""
    import re
    match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        content = re.sub(r"<title>.*?</title>", "", content, flags=re.IGNORECASE)
        return title, content
    # 첫 번째 H2에서 추출
    match = re.search(r"<h2[^>]*>(.*?)</h2>", content, re.IGNORECASE)
    if match:
        return match.group(1).strip(), content
    return "자동 생성 글", content


def run_pipeline(count=5, dry_run=False, pipeline="autoblog"):
    log.info("=" * 60)
    log.info(f"🚀 AutoBlog Engine v5.0 시작 — {count}편 발행 예정")
    log.info(f"   파이프라인: {pipeline} | 드라이런: {dry_run}")
    log.info(f"   사이트: {WP_URL}")
    log.info("=" * 60)

    km = KeywordManager()
    cg = ContentGenerator()
    im = ImageManager()
    am = AffiliateManager()
    wp = WordPressPublisher()
    sb = SupabaseLogger()

    keywords = km.select(count=count, pipeline=pipeline)
    if not keywords:
        log.error("❌ 사용 가능한 키워드 없음!")
        sb.log_alert("키워드 소진", "사용 가능한 키워드가 없습니다.", "critical", "keyword_exhausted")
        return

    log.info(f"📋 선택된 키워드 {len(keywords)}개:")
    for kw in keywords:
        log.info(f"   [{kw.get('type', 'traffic')}] {kw['keyword']}")

    success = 0
    fail = 0

    for i, kw_data in enumerate(keywords, 1):
        keyword = kw_data["keyword"]
        intent = kw_data.get("intent", "informational")
        category = kw_data.get("category", "")
        kw_type = kw_data.get("type", "traffic")

        log.info(f"\n{'='*50}")
        log.info(f"📝 [{i}/{len(keywords)}] '{keyword}' ({kw_type})")
        log.info(f"{'='*50}")

        # Step 1: AI 글 생성
        content, cost_usd, content_length = cg.generate(keyword, intent, category)
        if not content:
            fail += 1
            sb.log_publish({"keyword": keyword, "status": "failed",
                           "error_message": "AI 글 생성 실패", "pipeline": pipeline})
            continue

        log.info(f"✅ 글 생성 완료 ({content_length}자)")

        # Step 2: 제목 추출
        title, content = extract_title(content)
        log.info(f"📌 제목: {title}")

        # Step 3: 이미지 삽입
        img_data = im.fetch_image(keyword)
        content, has_image = im.insert_image(content, img_data)
        if has_image:
            log.info("🖼️ 이미지 삽입 완료")

        # Step 4: 제휴 링크 삽입
        content, has_coupang = am.insert_links(content, keyword, category)
        if has_coupang:
            log.info("🛒 제휴 링크 삽입 완료")

        # Step 5: 발행
        if dry_run:
            log.info(f"🔸 [DRY RUN] 발행 스킵: {title}")
            km.mark_used(keyword)
            success += 1
            continue

        result = wp.publish(title, content, category=category,
                           tags=[keyword, category] if category else [keyword])

        if result["status"] == "published":
            log.info(f"✅ 발행 성공: {result.get('url', '')}")
            km.mark_used(keyword)
            success += 1

            sb.log_publish({
                "title": title,
                "url": result.get("url", ""),
                "keyword": keyword,
                "intent": intent,
                "category": category,
                "pipeline": pipeline,
                "content_length": content_length,
                "has_image": has_image,
                "has_coupang": has_coupang,
                "status": "published"
            })
        else:
            fail += 1
            error_msg = result.get("error", "Unknown error")
            log.error(f"❌ 발행 실패: {error_msg}")

            sb.log_publish({
                "title": title,
                "keyword": keyword,
                "pipeline": pipeline,
                "status": "failed",
                "error_message": error_msg[:500]
            })

            if fail >= 3:
                sb.log_alert(
                    f"연속 발행 실패 {fail}건",
                    f"최근 키워드: {keyword}\n에러: {error_msg[:200]}",
                    "critical", "publish_fail"
                )

        # 요청 간 대기
        delay = random.randint(5, 15)
        log.info(f"⏳ {delay}초 대기...")
        time.sleep(delay)

    # 결과 요약
    log.info(f"\n{'='*60}")
    log.info(f"📊 실행 결과: 성공 {success}편 / 실패 {fail}편 / 총 {len(keywords)}편")
    log.info(f"{'='*60}")

    # Git commit (used keywords)
    _git_commit_used()


def _git_commit_used():
    """사용 키워드 파일을 git commit+push"""
    try:
        import subprocess
        subprocess.run(["git", "config", "user.email", "bot@autoblog.com"], cwd=ROOT, capture_output=True)
        subprocess.run(["git", "config", "user.name", "AutoBlog Bot"], cwd=ROOT, capture_output=True)
        subprocess.run(["git", "add", "data/used_keywords.json"], cwd=ROOT, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", f"chore: update used keywords {datetime.now(KST).strftime('%Y-%m-%d %H:%M')}"],
            cwd=ROOT, capture_output=True, text=True
        )
        if result.returncode == 0:
            subprocess.run(["git", "push"], cwd=ROOT, capture_output=True)
            log.info("📤 사용 키워드 Git push 완료")
    except Exception as e:
        log.warning(f"Git commit 실패 (무시): {e}")


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="AutoBlog Engine v5.0")
    parser.add_argument("--count", type=int, default=5, help="발행 편수")
    parser.add_argument("--dry-run", action="store_true", help="발행 없이 테스트")
    parser.add_argument("--pipeline", default="autoblog", help="파이프라인 (autoblog/hotdeal/promo)")
    args = parser.parse_args()

    if not WP_URL:
        log.error("❌ WP_URL 환경변수 없음")
        sys.exit(1)
    if not DEEPSEEK_KEY:
        log.error("❌ DEEPSEEK_API_KEY 환경변수 없음")
        sys.exit(1)

    run_pipeline(count=args.count, dry_run=args.dry_run, pipeline=args.pipeline)


if __name__ == "__main__":
    main()
