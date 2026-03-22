# AutoBlog Engine v5.0 — Cloudways WordPress

AI 자동 글 생성 + 발행 + Supabase 대시보드 연동

## 구조
```
scripts/main.py          — 메인 엔진 (키워드→생성→발행→로깅)
data/keywords.json       — 키워드 풀 (50개 초기)
data/affiliates.json     — 제휴 링크 설정
data/used_keywords.json  — 사용 완료 키워드
.github/workflows/publish.yml — 하루 4회 자동 실행
```

## GitHub Secrets 필수
- `WP_URL` — WordPress 사이트 URL
- `WP_USERNAME` — WordPress 관리자 아이디
- `WP_APP_PASSWORD` — WordPress 앱 비밀번호
- `DEEPSEEK_API_KEY` — DeepSeek API 키
- `CLAUDE_API_KEY` — Claude API 키 (선택, 폴리싱용)
- `UNSPLASH_ACCESS_KEY` — Unsplash API 키 (선택, 이미지용)
- `SUPABASE_URL` — Supabase 프로젝트 URL
- `SUPABASE_KEY` — Supabase anon key

## 실행
```bash
# 수동 실행
python scripts/main.py --count 3

# 드라이런 (발행 없이 테스트)
python scripts/main.py --count 1 --dry-run
```
