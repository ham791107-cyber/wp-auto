#!/usr/bin/env python3
"""
AutoBlog Engine v6.0 — AdSense 승인 최적화 + 품질 게이트
=========================================================
키워드 선택 → AI 글 생성 (멀티모델) → 품질 검증 → 이미지 삽입 (3중 폴백) →
제휴 링크 삽입 → AdSense HTML 최적화 → WordPress 발행 → Supabase 로깅

사용: python scripts/main.py [--dry-run] [--count 5] [--pipeline autoblog]
      python scripts/main.py --setup-pages          # 필수 페이지 자동 생성
"""

import os, sys, json, time, random, re, hashlib, logging, argparse
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
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY", "")
GROK_KEY = os.environ.get("GROK_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SITE_ID = os.environ.get("SITE_ID", "site-1")

# 네이버 카페 API
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
NAVER_REFRESH_TOKEN = os.environ.get("NAVER_REFRESH_TOKEN", "")
NAVER_CAFE_CLUBID = os.environ.get("NAVER_CAFE_CLUBID", "")
NAVER_CAFE_MENUID = os.environ.get("NAVER_CAFE_MENUID", "")

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
# 2. AI 글 생성 — 멀티모델 라우팅 + AdSense 최적화 프롬프트
# ═══════════════════════════════════════════════════════

DRAFT_PROMPT = """당신은 한국 최고의 금융·실용정보 블로거입니다.
10년 경력의 전문 필진처럼 깊이 있고 실용적인 글을 씁니다.

키워드: {keyword}
검색의도: {intent}
카테고리: {category}

=== 작성 규칙 (AdSense 승인 최적화) ===
1. 제목: 호기심+구체성 (숫자, 비교, 의문문 활용). <title> 태그로 감싸기
2. 도입부: 3~4문장, 독자 고민을 정확히 짚고 "이 글을 읽으면 ~를 알 수 있다" 약속
3. 본문: H2 소제목 5~7개, 각 소제목 아래 본문 300~500자
   - 구체적 수치·비교표·실제 사례 필수 (숫자 없는 문단 금지)
   - "~입니다", "~한 것입니다" 같은 딱딱한 종결 금지 → 대화체
   - 핵심 포인트는 <strong> 강조 (최소 5개)
   - 각 H2 섹션 사이에 충분한 내용 (광고 배치를 위한 자연스러운 문단 분리)
4. 마무리: 핵심 3줄 요약 + 구체적 행동 유도 (CTA)
5. 톤: 친근하되 전문적, "여러분" 호칭, 이모지 자제
6. 분량: 4,000~7,000자 (충분히 상세하게)
7. 키워드 배치: H2 2~3개에 키워드 자연스럽게 포함, 도입부·마무리에도 1회씩

=== HTML 구조 규칙 ===
- <title>글제목</title>을 콘텐츠 최상단에
- 본문은 <h2>, <p>, <strong>, <ul>/<ol> 태그만 사용
- <h1> 태그 사용 금지 (워드프레스가 자동 생성)
- 각 <p> 태그는 2~4문장으로 구성 (너무 길거나 짧지 않게)
- H2 사이 최소 2개 <p> 태그 확보 (광고 삽입 공간)
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
7. <strong> 태그 최소 5개 이상 사용
8. 4,000자 미만이면 내용을 보강하여 4,000자 이상으로

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

        draft = None
        draft_model = None

        if GROK_KEY:
            draft, draft_model = self._call_grok(prompt)
        if not draft and GEMINI_KEY:
            draft, draft_model = self._call_gemini(prompt)
        if not draft and DEEPSEEK_KEY:
            draft, draft_model = self._call_deepseek(prompt)

        if not draft:
            log.error(f"모든 모델 실패: {keyword}")
            return None, 0, 0

        log.info(f"초안 완료 [{draft_model}] ({len(draft)}자)")
        draft_cost = self._estimate_cost(draft_model, prompt, draft)

        if CLAUDE_KEY:
            polish_prompt = POLISH_PROMPT.format(keyword=keyword, draft=draft)
            polished = self._call_claude_polish(polish_prompt)
            if polished:
                polish_cost = self._estimate_cost("claude-sonnet-4-20250514", polish_prompt, polished)
                log.info(f"폴리싱 완료 [Claude Sonnet] ({len(polished)}자)")
                return polished, draft_cost + polish_cost, len(polished)

        return draft, draft_cost, len(draft)

    def _call_grok(self, prompt):
        import requests
        try:
            log.info("Grok 초안 생성 중...")
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROK_KEY}", "Content-Type": "application/json"},
                json={"model": "grok-3-mini", "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.8, "max_tokens": 5000},
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
            log.warning(f"Grok 실패: {e}")
            return None, None

    def _call_gemini(self, prompt):
        import requests
        try:
            log.info("Gemini 초안 생성 중...")
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.8, "maxOutputTokens": 5000}},
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
            log.warning(f"Gemini 실패: {e}")
            return None, None

    def _call_deepseek(self, prompt):
        import requests
        try:
            log.info("DeepSeek 초안 생성 중 (백업)...")
            resp = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.8, "max_tokens": 5000},
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
            log.warning(f"DeepSeek 실패: {e}")
            return None, None

    def _call_claude_polish(self, prompt):
        import requests
        try:
            log.info("Claude Sonnet 폴리싱 중...")
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CLAUDE_KEY, "anthropic-version": "2023-06-01",
                         "Content-Type": "application/json"},
                json={"model": "claude-sonnet-4-20250514", "max_tokens": 6000,
                      "messages": [{"role": "user", "content": prompt}]},
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
            log.warning(f"Claude 폴리싱 실패 (초안 그대로 사용): {e}")
            return None

    def _estimate_cost(self, model, prompt_text, output_text):
        input_t = len(prompt_text) // 4
        output_t = len(output_text) // 4
        r = self.COST_RATES.get(model, {"input": 0.001, "output": 0.002})
        return (input_t / 1000 * r["input"]) + (output_t / 1000 * r["output"])

    def _log_cost(self, model, provider, purpose, input_t, output_t):
        r = self.COST_RATES.get(model, {"input": 0.001, "output": 0.002})
        cost_usd = (input_t / 1000 * r["input"]) + (output_t / 1000 * r["output"])
        cost_krw = int(cost_usd * 1450)
        log.info(f"  {model}: {input_t}+{output_t} tokens = ${cost_usd:.4f} (W{cost_krw})")

        if SUPABASE_URL and SUPABASE_KEY:
            try:
                import requests
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/api_costs",
                    headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                             "Content-Type": "application/json", "Prefer": "return=minimal"},
                    json={"site_id": SITE_ID, "model": model, "provider": provider,
                          "purpose": purpose, "tokens_input": input_t, "tokens_output": output_t,
                          "cost_usd": round(cost_usd, 6), "cost_krw": cost_krw, "pipeline": "autoblog"},
                    timeout=10
                )
            except Exception:
                pass


# ═══════════════════════════════════════════════════════
# 3. 품질 게이트 — 발행 전 콘텐츠 검증 (100점 만점)
# ═══════════════════════════════════════════════════════
class QualityGate:
    """
    품질 채점 기준 (100점 만점):
    - 콘텐츠 길이: 25점 (4000자+ = 25, 3000+ = 20, 2000+ = 15, 1500+ = 10, 미만 = 5)
    - H2 소제목 수: 20점 (5~7개 = 20, 4개 = 17, 3개 = 12, 2개 = 8, 1개 이하 = 0)
    - 문단 품질: 15점 (평균 80~400자 = 15, 50~500자 = 10, 기타 = 5)
    - 이미지 포함: 15점 (있음 = 15, 없음 = 0)
    - 키워드 H2 포함: 10점 (H2에 키워드 존재 = 10, 없음 = 0)
    - <strong> 강조: 5점 (3개+ = 5, 1~2개 = 3, 없음 = 0)
    - CTA 존재: 5점 (행동유도 문구 있음 = 5, 없음 = 0)
    - HTML 구조: 5점 (h2+p 구조 정상 = 5, 비정상 = 0)
    """

    MIN_SCORE = 70

    def score(self, content, keyword, has_image=False):
        total = 0
        details = {}

        # 1. 콘텐츠 길이 (25점)
        length = len(content)
        if length >= 4000: pts = 25
        elif length >= 3000: pts = 20
        elif length >= 2000: pts = 15
        elif length >= 1500: pts = 10
        else: pts = 5
        total += pts
        details['length'] = f"{length}자 ({pts}점)"

        # 2. H2 소제목 수 (20점)
        h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', content, re.IGNORECASE)
        h2_count = len(h2s)
        if 5 <= h2_count <= 7: pts = 20
        elif h2_count == 4: pts = 17
        elif h2_count == 3: pts = 12
        elif h2_count == 2 or h2_count == 8: pts = 8
        else: pts = 0
        total += pts
        details['h2_count'] = f"{h2_count}개 ({pts}점)"

        # 3. 문단 품질 (15점)
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.IGNORECASE | re.DOTALL)
        if paragraphs:
            avg_len = sum(len(re.sub(r'<[^>]+>', '', p)) for p in paragraphs) / len(paragraphs)
            if 80 <= avg_len <= 400: pts = 15
            elif 50 <= avg_len <= 500: pts = 10
            else: pts = 5
        else:
            avg_len = 0
            pts = 0
        total += pts
        details['paragraphs'] = f"{len(paragraphs)}개, 평균 {avg_len:.0f}자 ({pts}점)"

        # 4. 이미지 포함 (15점)
        img_in_content = '<img' in content.lower()
        pts = 15 if (has_image or img_in_content) else 0
        total += pts
        details['image'] = f"{'있음' if pts else '없음'} ({pts}점)"

        # 5. 키워드 H2 포함 (10점)
        kw_words = keyword.lower().split()
        kw_in_h2 = sum(1 for h2 in h2s if any(w in h2.lower() for w in kw_words if len(w) > 1))
        pts = 10 if kw_in_h2 >= 2 else (6 if kw_in_h2 == 1 else 0)
        total += pts
        details['keyword_h2'] = f"{kw_in_h2}개 H2 ({pts}점)"

        # 6. <strong> 강조 (5점)
        strong_count = len(re.findall(r'<strong>', content, re.IGNORECASE))
        pts = 5 if strong_count >= 3 else (3 if strong_count >= 1 else 0)
        total += pts
        details['strong'] = f"{strong_count}개 ({pts}점)"

        # 7. CTA 존재 (5점)
        cta_patterns = ['확인해', '시작해', '신청', '추천', '클릭', '바로가기', '지금', '놓치지']
        has_cta = any(p in content for p in cta_patterns)
        pts = 5 if has_cta else 0
        total += pts
        details['cta'] = f"{'있음' if has_cta else '없음'} ({pts}점)"

        # 8. HTML 구조 (5점)
        has_proper = '<h2' in content and '<p' in content and '</p>' in content
        pts = 5 if has_proper else 0
        total += pts
        details['structure'] = f"{'정상' if has_proper else '비정상'} ({pts}점)"

        return total, details

    def validate(self, content, keyword, has_image=False):
        score, details = self.score(content, keyword, has_image)
        passed = score >= self.MIN_SCORE
        log.info(f"  품질 점수: {score}/100 ({'PASS' if passed else 'FAIL'})")
        for k, v in details.items():
            log.info(f"    {k}: {v}")
        return passed, score, details


# ═══════════════════════════════════════════════════════
# 4. 이미지 삽입 — 3중 폴백 (Pexels → Pixabay → Unsplash)
# ═══════════════════════════════════════════════════════
class ImageManager:
    """이미지 3중 폴백: Pexels(1순위) → Pixabay(2순위) → Unsplash(백업)"""

    def fetch_image(self, keyword):
        """3중 폴백으로 이미지 검색"""
        # 1순위: Pexels (고품질 무료)
        if PEXELS_KEY:
            result = self._fetch_pexels(keyword)
            if result:
                return result

        # 2순위: Pixabay (대량 무료)
        if PIXABAY_KEY:
            result = self._fetch_pixabay(keyword)
            if result:
                return result

        # 3순위: Unsplash (백업)
        if UNSPLASH_KEY:
            result = self._fetch_unsplash(keyword)
            if result:
                return result

        log.warning(f"모든 이미지 API 실패: {keyword}")
        return None

    def _fetch_pexels(self, keyword):
        import requests
        try:
            log.info("  Pexels 이미지 검색 중...")
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": keyword, "per_page": 5, "orientation": "landscape", "size": "large"},
                timeout=10
            )
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            if photos:
                img = random.choice(photos[:3])
                log.info(f"  Pexels 이미지 확보: {img['photographer']}")
                return {
                    "url": img["src"]["large2x"],
                    "alt": keyword,
                    "credit": img["photographer"],
                    "link": img["photographer_url"],
                    "source": "Pexels"
                }
        except Exception as e:
            log.warning(f"  Pexels 실패: {e}")
        return None

    def _fetch_pixabay(self, keyword):
        import requests
        try:
            log.info("  Pixabay 이미지 검색 중...")
            resp = requests.get(
                "https://pixabay.com/api/",
                params={
                    "key": PIXABAY_KEY, "q": keyword, "per_page": 5,
                    "orientation": "horizontal", "image_type": "photo",
                    "min_width": 1200, "safesearch": "true"
                },
                timeout=10
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            if hits:
                img = random.choice(hits[:3])
                log.info(f"  Pixabay 이미지 확보: {img.get('user', 'unknown')}")
                return {
                    "url": img["largeImageURL"],
                    "alt": keyword,
                    "credit": img.get("user", "Pixabay"),
                    "link": img.get("pageURL", "https://pixabay.com"),
                    "source": "Pixabay"
                }
        except Exception as e:
            log.warning(f"  Pixabay 실패: {e}")
        return None

    def _fetch_unsplash(self, keyword):
        import requests
        try:
            log.info("  Unsplash 이미지 검색 중 (백업)...")
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
                log.info(f"  Unsplash 이미지 확보: {img['user']['name']}")
                return {
                    "url": img["urls"]["regular"],
                    "alt": img.get("alt_description", keyword),
                    "credit": img["user"]["name"],
                    "link": img["user"]["links"]["html"],
                    "source": "Unsplash"
                }
        except Exception as e:
            log.warning(f"  Unsplash 실패: {e}")
        return None

    def insert_image(self, content, image_data):
        """콘텐츠 첫 번째 H2 앞에 이미지 삽입"""
        if not image_data:
            return content, False, ""

        source = image_data.get("source", "Unknown")
        img_html = (
            f'<figure style="margin:24px 0">'
            f'<img src="{image_data["url"]}" alt="{image_data["alt"]}" '
            f'style="width:100%;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.1)" loading="lazy"/>'
            f'<figcaption style="text-align:center;font-size:12px;color:#888;margin-top:8px;">'
            f'Photo by <a href="{image_data["link"]}?utm_source=autoblog" target="_blank">'
            f'{image_data["credit"]}</a> on {source}</figcaption>'
            f'</figure>'
        )

        if "<h2" in content:
            idx = content.index("<h2")
            return content[:idx] + img_html + content[idx:], True, source
        return img_html + content, True, source


# ═══════════════════════════════════════════════════════
# 5. 제휴 링크 삽입
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
            if "</h2>" in content:
                parts = content.rsplit("</h2>", 1)
                content = parts[0] + "</h2>" + link_html + parts[1]
            else:
                content += link_html

        return content, bool(matched_links)

    def _build_product_box(self, links):
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
                f'{name} 최저가 확인하기</a></li>'
            )

        if not items:
            return ""

        return (
            f'\n<div style="background:#f8f9ff;border:2px solid #dde3ff;'
            f'border-radius:12px;padding:20px;margin:24px 0">'
            f'<p style="font-weight:700;font-size:16px;margin:0 0 12px">추천 상품</p>'
            f'<ul style="list-style:none;padding:0;margin:0">{items}</ul>'
            f'<p style="font-size:11px;color:#999;margin:12px 0 0">'
            f'이 포스팅은 쿠팡 파트너스 활동의 일환으로, 일정액의 수수료를 제공받을 수 있습니다.</p>'
            f'</div>\n'
        )


# ═══════════════════════════════════════════════════════
# 6. AdSense HTML 최적화 — 발행 전 후처리
# ═══════════════════════════════════════════════════════
class AdSenseOptimizer:
    """발행 전 HTML 구조를 AdSense 친화적으로 정리"""

    def optimize(self, content):
        # 1. H2 사이에 충분한 간격 확보 (Ad Inserter 플러그인용)
        content = re.sub(
            r'(</h2>)\s*(<h2)',
            r'\1\n<p style="margin:12px 0">&nbsp;</p>\n\2',
            content
        )

        # 2. 빈 P 태그 정리
        content = re.sub(r'<p>\s*</p>', '', content)

        # 3. 연속된 <br> 정리
        content = re.sub(r'(<br\s*/?>){3,}', '<br/><br/>', content)

        # 4. 목차 스타일 개선 (이미 있으면 스킵)
        if '<ul' not in content[:500] and content.count('<h2') >= 4:
            toc = self._generate_toc(content)
            if toc:
                # 첫 번째 H2 앞에 목차 삽입
                if '<h2' in content:
                    idx = content.index('<h2')
                    content = content[:idx] + toc + content[idx:]

        return content

    def _generate_toc(self, content):
        """H2 기반 간단 목차 생성"""
        h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', content, re.IGNORECASE)
        if len(h2s) < 4:
            return ""

        items = ""
        for i, h2 in enumerate(h2s, 1):
            clean = re.sub(r'<[^>]+>', '', h2).strip()
            items += f'<li style="margin:4px 0"><a href="#section-{i}" style="color:#4a5568;text-decoration:none">{clean}</a></li>'

        return (
            f'<div style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:12px;'
            f'padding:16px 20px;margin:20px 0">'
            f'<p style="font-weight:700;font-size:14px;margin:0 0 8px;color:#1a1a2e">목차</p>'
            f'<ol style="margin:0;padding-left:20px;color:#4a5568;font-size:13px">{items}</ol>'
            f'</div>\n'
        )


# ═══════════════════════════════════════════════════════
# 7. WordPress 발행
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
        import requests
        cat_id = self._get_or_create_category(category) if category else None

        post_data = {"title": title, "content": content, "status": "publish", "format": "standard"}
        if cat_id:
            post_data["categories"] = [cat_id]
        if tags:
            tag_ids = [self._get_or_create_tag(t) for t in tags[:5]]
            post_data["tags"] = [t for t in tag_ids if t]

        try:
            resp = requests.post(
                f"{self.url}/wp-json/wp/v2/posts", headers=self.headers,
                json=post_data, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            return {"id": data["id"], "url": data.get("link", ""),
                    "title": data.get("title", {}).get("rendered", title), "status": "published"}
        except Exception as e:
            log.error(f"발행 실패: {e}")
            return {"status": "failed", "error": str(e)}

    def _get_or_create_category(self, name):
        import requests
        try:
            resp = requests.get(f"{self.url}/wp-json/wp/v2/categories",
                               headers=self.headers, params={"search": name, "per_page": 5}, timeout=10)
            for c in resp.json():
                if c["name"].lower() == name.lower():
                    return c["id"]
            resp = requests.post(f"{self.url}/wp-json/wp/v2/categories",
                                headers=self.headers, json={"name": name}, timeout=10)
            return resp.json().get("id")
        except Exception:
            return None

    def _get_or_create_tag(self, name):
        import requests
        try:
            resp = requests.get(f"{self.url}/wp-json/wp/v2/tags",
                               headers=self.headers, params={"search": name, "per_page": 5}, timeout=10)
            for t in resp.json():
                if t["name"].lower() == name.lower():
                    return t["id"]
            resp = requests.post(f"{self.url}/wp-json/wp/v2/tags",
                                headers=self.headers, json={"name": name}, timeout=10)
            return resp.json().get("id")
        except Exception:
            return None


# ═══════════════════════════════════════════════════════
# 8. 필수 페이지 자동 생성 (AdSense 승인용, 중복 방지)
# ═══════════════════════════════════════════════════════
class EssentialPagesCreator:
    """About/개인정보처리방침/연락처/면책고지/이용약관 자동 생성.
    이미 존재하는 페이지는 건너뜀 (slug 기반 중복 체크)."""

    PAGES = [
        {
            "slug": "about",
            "title": "소개",
            "content": """<h2>블로그 소개</h2>
<p>안녕하세요! <strong>{site_name}</strong>에 오신 것을 환영합니다.</p>
<p>저희 블로그는 독자 여러분께 유용하고 정확한 정보를 제공하기 위해 운영되고 있습니다.
전문 필진이 직접 조사하고 검증한 내용만을 다루며, 여러분의 일상에 실질적인 도움이 되는
양질의 콘텐츠를 만들기 위해 노력하고 있습니다.</p>
<h2>운영 목적</h2>
<p>복잡한 정보를 쉽고 명확하게 전달하여, 누구나 올바른 의사결정을 할 수 있도록 돕는 것이
저희의 목표입니다. 재테크, 금융, IT, 생활 정보 등 실용적인 분야를 중심으로 콘텐츠를
발행하고 있습니다.</p>
<h2>연락처</h2>
<p>문의사항이 있으시면 <a href="/contact">문의 페이지</a>를 통해 연락해 주세요.</p>"""
        },
        {
            "slug": "privacy-policy",
            "title": "개인정보처리방침",
            "content": """<h2>개인정보처리방침</h2>
<p><strong>{site_name}</strong>(이하 '사이트')은 이용자의 개인정보를 중요하게 생각하며,
「개인정보 보호법」을 준수하고 있습니다.</p>
<h3>1. 수집하는 개인정보 항목</h3>
<p>사이트는 서비스 제공을 위해 필요한 최소한의 개인정보를 수집합니다.</p>
<ul>
<li>댓글 작성 시: 이름, 이메일 주소</li>
<li>자동 수집: 접속 IP, 쿠키, 방문 일시, 서비스 이용 기록</li>
</ul>
<h3>2. 개인정보의 이용 목적</h3>
<ul>
<li>서비스 제공 및 운영</li>
<li>이용자 문의 응대</li>
<li>사이트 이용 통계 분석</li>
</ul>
<h3>3. 개인정보의 보유 및 이용 기간</h3>
<p>이용자의 개인정보는 수집 목적이 달성된 후 즉시 파기합니다.
단, 관련 법령에 의해 보존이 필요한 경우 해당 기간 동안 보관합니다.</p>
<h3>4. 쿠키(Cookie) 사용</h3>
<p>사이트는 이용자에게 맞춤형 서비스를 제공하기 위해 쿠키를 사용합니다.
이용자는 브라우저 설정에서 쿠키 허용을 관리할 수 있습니다.</p>
<h3>5. 광고</h3>
<p>사이트는 Google AdSense를 포함한 제3자 광고 서비스를 이용할 수 있습니다.
이러한 광고 서비스 제공업체는 사용자의 관심사에 맞는 광고를 게재하기 위해
쿠키를 사용할 수 있습니다.</p>
<h3>6. 개인정보 보호 책임자</h3>
<p>개인정보 관련 문의는 <a href="/contact">문의 페이지</a>를 통해 연락해 주세요.</p>
<p><em>시행일: {date}</em></p>"""
        },
        {
            "slug": "contact",
            "title": "문의하기",
            "content": """<h2>문의하기</h2>
<p>블로그에 대한 문의, 제안, 협업 요청 등 무엇이든 환영합니다.</p>
<h3>문의 방법</h3>
<p>아래 이메일로 연락해 주시면 빠른 시일 내에 답변 드리겠습니다.</p>
<p><strong>이메일:</strong> {email}</p>
<h3>문의 시 참고사항</h3>
<ul>
<li>광고 및 협업 관련 문의는 구체적인 내용을 함께 보내주세요.</li>
<li>콘텐츠 수정 요청은 해당 글의 URL을 포함해 주세요.</li>
<li>답변은 영업일 기준 1~3일 이내에 드립니다.</li>
</ul>"""
        },
        {
            "slug": "disclaimer",
            "title": "면책 고지",
            "content": """<h2>면책 고지 (Disclaimer)</h2>
<h3>정보의 정확성</h3>
<p><strong>{site_name}</strong>에서 제공하는 정보는 참고 목적으로 제공되며,
정확성이나 완전성을 보장하지 않습니다. 중요한 의사결정 시에는 반드시
전문가의 조언을 구하시기 바랍니다.</p>
<h3>제휴 링크 고지</h3>
<p>이 사이트의 일부 링크는 제휴(어필리에이트) 링크입니다.
이러한 링크를 통해 제품을 구매하시면 사이트 운영에 도움이 되는
소정의 수수료를 받을 수 있습니다. 이는 이용자에게 추가 비용을 발생시키지 않습니다.</p>
<p>이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>
<h3>외부 링크</h3>
<p>사이트에 포함된 외부 링크의 내용에 대해서는 책임을 지지 않습니다.</p>
<h3>투자 관련 면책</h3>
<p>본 사이트에서 제공하는 금융 관련 정보는 투자 권유가 아니며,
투자에 따른 손실에 대해 책임을 지지 않습니다.</p>
<p><em>시행일: {date}</em></p>"""
        },
        {
            "slug": "terms",
            "title": "이용약관",
            "content": """<h2>이용약관</h2>
<h3>제1조 (목적)</h3>
<p>이 약관은 <strong>{site_name}</strong>(이하 '사이트')이 제공하는 서비스의
이용 조건 및 절차에 관한 사항을 규정함을 목적으로 합니다.</p>
<h3>제2조 (이용자의 의무)</h3>
<ul>
<li>이용자는 사이트 이용 시 관련 법령을 준수해야 합니다.</li>
<li>타인의 개인정보를 도용하거나 허위 정보를 기재해서는 안 됩니다.</li>
<li>사이트의 콘텐츠를 무단으로 복제, 배포, 수정해서는 안 됩니다.</li>
</ul>
<h3>제3조 (저작권)</h3>
<p>사이트에 게시된 모든 콘텐츠의 저작권은 사이트 운영자에게 있습니다.
무단 전재 및 재배포를 금지합니다.</p>
<h3>제4조 (면책)</h3>
<p>사이트는 이용자가 사이트의 정보를 이용하여 발생한 손해에 대해
책임을 지지 않습니다.</p>
<h3>제5조 (약관의 변경)</h3>
<p>사이트는 필요 시 약관을 변경할 수 있으며, 변경된 약관은
사이트에 공지한 시점부터 효력이 발생합니다.</p>
<p><em>시행일: {date}</em></p>"""
        },
    ]

    def __init__(self):
        import base64
        self.url = WP_URL.rstrip("/")
        cred = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/json"
        }

    def create_all(self, site_name="", email="contact@example.com"):
        import requests
        date_str = datetime.now(KST).strftime("%Y년 %m월 %d일")
        if not site_name:
            site_name = WP_URL.replace("https://", "").replace("http://", "").split("/")[0]

        created = []
        skipped = []
        failed = []

        for page in self.PAGES:
            slug = page["slug"]

            # ── 중복 체크: slug로 기존 페이지 검색 ──
            try:
                resp = requests.get(
                    f"{self.url}/wp-json/wp/v2/pages",
                    headers=self.headers,
                    params={"slug": slug, "per_page": 1, "status": "any"},
                    timeout=10
                )
                existing = resp.json()
                if isinstance(existing, list) and len(existing) > 0:
                    log.info(f"  '{page['title']}' ({slug}) 이미 존재 — 건너뜀")
                    skipped.append(page["title"])
                    continue
            except Exception as e:
                log.warning(f"  '{page['title']}' 중복 확인 실패, 생성 시도: {e}")

            # ── 페이지 생성 ──
            content = page["content"].format(
                site_name=site_name, date=date_str, email=email
            )

            try:
                resp = requests.post(
                    f"{self.url}/wp-json/wp/v2/pages",
                    headers=self.headers,
                    json={"title": page["title"], "slug": slug, "content": content, "status": "publish"},
                    timeout=15
                )
                resp.raise_for_status()
                url = resp.json().get("link", "")
                log.info(f"  '{page['title']}' 페이지 생성 완료: {url}")
                created.append(page["title"])
            except Exception as e:
                log.error(f"  '{page['title']}' 페이지 생성 실패: {e}")
                failed.append(page["title"])

        log.info(f"\n  필수 페이지 결과: 생성 {len(created)}개 / 이미 존재 {len(skipped)}개 / 실패 {len(failed)}개")
        return created, skipped, failed


# ═══════════════════════════════════════════════════════
# 9. Supabase 로깅
# ═══════════════════════════════════════════════════════
class SupabaseLogger:
    def __init__(self):
        self.url = SUPABASE_URL
        self.key = SUPABASE_KEY
        self.headers = {
            "apikey": self.key, "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json", "Prefer": "return=minimal"
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
                "image_tier": data.get("image_source", ""),
                "has_coupang": data.get("has_coupang", False),
                "quality_score": data.get("quality_score", 0),
                "sns_shared": json.dumps(data.get("sns_shared", [])),
                "status": data.get("status", "published"),
                "error_message": data.get("error_message", ""),
                "published_at": datetime.now(KST).isoformat(),
            }
            requests.post(
                f"{self.url}/rest/v1/publish_logs", headers=self.headers,
                json=record, timeout=10
            )
            log.info(f"  Supabase 로그 기록: {data.get('title', '')[:30]}")
        except Exception as e:
            log.warning(f"Supabase 로깅 실패: {e}")

    def log_alert(self, title, message, severity="warning", alert_type="info"):
        if not self.url or not self.key:
            return
        import requests
        try:
            requests.post(
                f"{self.url}/rest/v1/alerts", headers=self.headers,
                json={"site_id": SITE_ID, "alert_type": alert_type,
                      "severity": severity, "title": title, "message": message},
                timeout=10
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════
# 10. 네이버 카페 자동 공유
# ═══════════════════════════════════════════════════════
class NaverCafePublisher:
    """네이버 카페 API로 글 자동 공유.
    OAuth 2.0 Refresh Token으로 Access Token 자동 갱신."""

    TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
    CAFE_API = "https://openapi.naver.com/v1/cafe/{clubid}/menu/{menuid}/articles"

    def __init__(self):
        self.access_token = None
        self.clubid = NAVER_CAFE_CLUBID
        self.menuid = NAVER_CAFE_MENUID

    def is_configured(self):
        return all([NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_REFRESH_TOKEN,
                    self.clubid, self.menuid])

    def _refresh_access_token(self):
        """Refresh Token으로 새 Access Token 발급"""
        import requests
        try:
            resp = requests.post(self.TOKEN_URL, params={
                "grant_type": "refresh_token",
                "client_id": NAVER_CLIENT_ID,
                "client_secret": NAVER_CLIENT_SECRET,
                "refresh_token": NAVER_REFRESH_TOKEN,
            }, timeout=10)
            data = resp.json()
            if "access_token" in data:
                self.access_token = data["access_token"]
                log.info("  네이버 Access Token 갱신 완료")
                return True
            else:
                log.warning(f"  네이버 토큰 갱신 실패: {data.get('error_description', data)}")
                return False
        except Exception as e:
            log.warning(f"  네이버 토큰 갱신 실패: {e}")
            return False

    def publish(self, title, content, wp_url=""):
        """카페에 글 공유. HTML 콘텐츠를 그대로 전송."""
        import requests
        import urllib.parse

        if not self.is_configured():
            return None

        if not self.access_token:
            if not self._refresh_access_token():
                return None

        url = self.CAFE_API.format(clubid=self.clubid, menuid=self.menuid)

        # 원문 링크 추가
        footer = ""
        if wp_url:
            footer = (
                f'\n<p style="margin-top:24px;padding-top:16px;border-top:1px solid #eee;'
                f'font-size:13px;color:#888;">'
                f'원문: <a href="{wp_url}" target="_blank">{wp_url}</a></p>'
            )

        cafe_content = content + footer

        try:
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                data={
                    "subject": urllib.parse.quote(title),
                    "content": urllib.parse.quote(cafe_content),
                    "openyn": "true",
                    "searchopen": "true",
                    "replyyn": "true",
                },
                timeout=15
            )

            if resp.status_code == 200:
                result = resp.json()
                article_url = result.get("message", {}).get("result", {}).get("articleUrl", "")
                log.info(f"  네이버 카페 공유 완료: {article_url}")
                return article_url
            elif resp.status_code == 401:
                # 토큰 만료 → 재발급 후 재시도
                log.info("  네이버 토큰 만료, 재발급 시도...")
                if self._refresh_access_token():
                    return self.publish(title, content, wp_url)
                return None
            else:
                log.warning(f"  네이버 카페 공유 실패: {resp.status_code} {resp.text[:200]}")
                return None
        except Exception as e:
            log.warning(f"  네이버 카페 공유 실패: {e}")
            return None


# ═══════════════════════════════════════════════════════
# 11. API 상태 체크 — Supabase에 연결 상태 기록
# ═══════════════════════════════════════════════════════
def check_api_status():
    """모든 API 키 설정 상태를 확인하고 Supabase에 기록"""
    status = {
        "last_checked": datetime.now(KST).isoformat(),
        "wp": bool(WP_URL and WP_USER and WP_PASS),
        "deepseek": bool(DEEPSEEK_KEY),
        "claude": bool(CLAUDE_KEY),
        "grok": bool(GROK_KEY),
        "gemini": bool(GEMINI_KEY),
        "pexels": bool(PEXELS_KEY),
        "pixabay": bool(PIXABAY_KEY),
        "unsplash": bool(UNSPLASH_KEY),
        "supabase": bool(SUPABASE_URL and SUPABASE_KEY),
        "naver_cafe": bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET and NAVER_REFRESH_TOKEN
                           and NAVER_CAFE_CLUBID and NAVER_CAFE_MENUID),
    }

    log.info("API 상태 체크:")
    for name, ok in status.items():
        if name == "last_checked":
            continue
        log.info(f"  {name}: {'OK' if ok else 'X'}")

    # Supabase에 기록
    if SUPABASE_URL and SUPABASE_KEY:
        import requests
        try:
            # 기존 설정 가져오기
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/dashboard_config?id=eq.global",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=10
            )
            existing = {}
            rows = resp.json()
            if rows and len(rows) > 0:
                existing = rows[0].get("settings", {})

            existing["api_status"] = status

            requests.patch(
                f"{SUPABASE_URL}/rest/v1/dashboard_config?id=eq.global",
                headers={
                    "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json", "Prefer": "return=minimal"
                },
                json={"settings": existing, "updated_at": datetime.now(KST).isoformat()},
                timeout=10
            )
            log.info("  API 상태 Supabase 기록 완료")
        except Exception as e:
            log.warning(f"  API 상태 기록 실패: {e}")

    return status


# ═══════════════════════════════════════════════════════
# 12. 메인 파이프라인
# ═══════════════════════════════════════════════════════
def extract_title(content):
    match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
        content = re.sub(r"<title>.*?</title>", "", content, flags=re.IGNORECASE)
        return title, content
    match = re.search(r"<h2[^>]*>(.*?)</h2>", content, re.IGNORECASE)
    if match:
        return match.group(1).strip(), content
    return "자동 생성 글", content


def _get_site_config():
    """Supabase에서 사이트 설정 조회 (daily_target, status)"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    import requests
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/sites?id=eq.{SITE_ID}",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=10
        )
        rows = resp.json()
        if rows and len(rows) > 0:
            return rows[0]
    except Exception:
        pass
    return None


def run_pipeline(count=5, dry_run=False, pipeline="autoblog"):
    # Supabase에서 사이트 설정 조회
    site_config = _get_site_config()
    if site_config:
        # 일시정지 상태 확인
        if site_config.get("status") == "paused":
            log.info("이 사이트는 일시정지 상태입니다. 발행을 건너뜁니다.")
            return

        # 대시보드에서 설정한 daily_target 사용 (CLI 기본값일 때만)
        db_target = site_config.get("daily_target")
        if db_target and count == 5:  # 5는 CLI 기본값
            count = db_target
            log.info(f"  Supabase daily_target 적용: {count}편")

    log.info("=" * 60)
    log.info(f"AutoBlog Engine v6.0 시작 — {count}편 발행 예정")
    log.info(f"  파이프라인: {pipeline} | 드라이런: {dry_run}")
    log.info(f"  사이트: {WP_URL}")
    log.info(f"  이미지: Pexels{'(O)' if PEXELS_KEY else '(X)'} → "
             f"Pixabay{'(O)' if PIXABAY_KEY else '(X)'} → "
             f"Unsplash{'(O)' if UNSPLASH_KEY else '(X)'}")
    log.info(f"  네이버 카페: {'(O)' if NAVER_REFRESH_TOKEN else '(X)'}")
    log.info("=" * 60)

    # API 상태 체크 (매 실행 시)
    check_api_status()

    km = KeywordManager()
    cg = ContentGenerator()
    im = ImageManager()
    am = AffiliateManager()
    ao = AdSenseOptimizer()
    qg = QualityGate()
    nc = NaverCafePublisher()
    wp = WordPressPublisher()
    sb = SupabaseLogger()

    keywords = km.select(count=count, pipeline=pipeline)
    if not keywords:
        log.error("사용 가능한 키워드 없음!")
        sb.log_alert("키워드 소진", "사용 가능한 키워드가 없습니다.", "critical", "keyword_exhausted")
        return

    log.info(f"선택된 키워드 {len(keywords)}개:")
    for kw in keywords:
        log.info(f"  [{kw.get('type', 'traffic')}] {kw['keyword']}")

    success = 0
    fail = 0

    for i, kw_data in enumerate(keywords, 1):
        keyword = kw_data["keyword"]
        intent = kw_data.get("intent", "informational")
        category = kw_data.get("category", "")
        kw_type = kw_data.get("type", "traffic")

        log.info(f"\n{'='*50}")
        log.info(f"[{i}/{len(keywords)}] '{keyword}' ({kw_type})")
        log.info(f"{'='*50}")

        # Step 1: AI 글 생성
        content, cost_usd, content_length = cg.generate(keyword, intent, category)
        if not content:
            fail += 1
            sb.log_publish({"keyword": keyword, "status": "failed",
                           "error_message": "AI 글 생성 실패", "pipeline": pipeline})
            continue

        log.info(f"글 생성 완료 ({content_length}자)")

        # Step 2: 제목 추출
        title, content = extract_title(content)
        log.info(f"제목: {title}")

        # Step 3: 이미지 삽입 (3중 폴백)
        img_data = im.fetch_image(keyword)
        content, has_image, image_source = im.insert_image(content, img_data)
        if has_image:
            log.info(f"이미지 삽입 완료 [{image_source}]")

        # Step 4: 제휴 링크 삽입
        content, has_coupang = am.insert_links(content, keyword, category)
        if has_coupang:
            log.info("제휴 링크 삽입 완료")

        # Step 5: AdSense HTML 최적화
        content = ao.optimize(content)
        log.info("AdSense HTML 최적화 완료")

        # Step 6: 품질 검증
        passed, quality_score, q_details = qg.validate(content, keyword, has_image)

        if not passed:
            log.warning(f"품질 미달 ({quality_score}/100) — 그래도 발행 진행 (기록)")
            sb.log_alert(
                f"품질 미달: {keyword}",
                f"점수 {quality_score}/100. 항목: {json.dumps(q_details, ensure_ascii=False)[:300]}",
                "warning", "quality_low"
            )

        # Step 7: 발행
        if dry_run:
            log.info(f"[DRY RUN] 발행 스킵: {title} (품질: {quality_score}/100)")
            km.mark_used(keyword)
            success += 1
            continue

        result = wp.publish(title, content, category=category,
                           tags=[keyword, category] if category else [keyword])

        if result["status"] == "published":
            log.info(f"발행 성공: {result.get('url', '')} (품질: {quality_score}/100)")
            km.mark_used(keyword)
            success += 1

            # Step 8: 네이버 카페 자동 공유
            sns_shared = []
            if nc.is_configured():
                cafe_url = nc.publish(title, content, wp_url=result.get("url", ""))
                if cafe_url:
                    sns_shared.append("naver_cafe")

            sb.log_publish({
                "title": title, "url": result.get("url", ""),
                "keyword": keyword, "intent": intent, "category": category,
                "pipeline": pipeline, "content_length": content_length,
                "has_image": has_image, "image_source": image_source,
                "has_coupang": has_coupang,
                "quality_score": quality_score,
                "sns_shared": sns_shared,
                "status": "published"
            })
        else:
            fail += 1
            error_msg = result.get("error", "Unknown error")
            log.error(f"발행 실패: {error_msg}")

            sb.log_publish({
                "title": title, "keyword": keyword, "pipeline": pipeline,
                "quality_score": quality_score,
                "status": "failed", "error_message": error_msg[:500]
            })

            if fail >= 3:
                sb.log_alert(f"연속 발행 실패 {fail}건",
                            f"최근 키워드: {keyword}\n에러: {error_msg[:200]}",
                            "critical", "publish_fail")

        delay = random.randint(5, 15)
        log.info(f"  {delay}초 대기...")
        time.sleep(delay)

    log.info(f"\n{'='*60}")
    log.info(f"실행 결과: 성공 {success}편 / 실패 {fail}편 / 총 {len(keywords)}편")
    log.info(f"{'='*60}")

    _git_commit_used()


def _git_commit_used():
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
            log.info("사용 키워드 Git push 완료")
    except Exception as e:
        log.warning(f"Git commit 실패 (무시): {e}")


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="AutoBlog Engine v6.0")
    parser.add_argument("--count", type=int, default=5, help="발행 편수")
    parser.add_argument("--dry-run", action="store_true", help="발행 없이 테스트")
    parser.add_argument("--pipeline", default="autoblog", help="파이프라인 (autoblog/hotdeal/promo)")
    parser.add_argument("--setup-pages", action="store_true", help="AdSense 필수 페이지 자동 생성")
    parser.add_argument("--check-status", action="store_true", help="API 연결 상태 체크 → Supabase 기록")
    parser.add_argument("--site-name", default="", help="사이트 이름 (필수 페이지용)")
    parser.add_argument("--email", default="contact@example.com", help="연락처 이메일")
    args = parser.parse_args()

    # API 상태 체크 모드
    if args.check_status:
        check_api_status()
        sys.exit(0)

    # 필수 페이지 생성 모드
    if args.setup_pages:
        if not WP_URL or not WP_USER or not WP_PASS:
            log.error("WP_URL, WP_USERNAME, WP_APP_PASSWORD 환경변수 필요")
            sys.exit(1)
        log.info("=" * 60)
        log.info("AdSense 필수 페이지 자동 생성")
        log.info("=" * 60)
        epc = EssentialPagesCreator()
        created, skipped, failed = epc.create_all(site_name=args.site_name, email=args.email)
        sys.exit(0 if not failed else 1)

    # 일반 발행 모드
    if not WP_URL:
        log.error("WP_URL 환경변수 없음")
        sys.exit(1)
    if not (DEEPSEEK_KEY or GROK_KEY or GEMINI_KEY):
        log.error("AI API 키가 하나도 없음 (DEEPSEEK/GROK/GEMINI 중 1개 필요)")
        sys.exit(1)

    run_pipeline(count=args.count, dry_run=args.dry_run, pipeline=args.pipeline)


if __name__ == "__main__":
    main()
