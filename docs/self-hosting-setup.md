# AutoBlog 셀프 호스팅 — Fork 후 설정 매뉴얼

> GitHub Fork 완료 후, 대시보드 연동 + 블로그 자동 발행까지의 전체 과정

---

## 전체 구조도

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  WordPress   │◄───│ GitHub Actions│◄───│  Dashboard   │
│  (내 블로그)  │    │ (자동 발행)    │    │  (Vercel)    │
└─────────────┘    └──────┬───────┘    └──────┬───────┘
                          │                    │
                   ┌──────▼────────────────────▼───────┐
                   │         Supabase (DB + Auth)       │
                   └───────────────────────────────────┘
```

| 구성요소 | 역할 | 비용 |
|---------|------|------|
| WordPress (Cloudways) | 블로그 호스팅 | $11/월 |
| GitHub (Fork) | AI 발행 엔진 자동 실행 | 무료 |
| Gemini API | AI 글 작성 | 무료 |
| Supabase | DB + 사용자 인증 | 무료 |
| Vercel | 대시보드 웹 배포 | 무료 |

---

## 사전 준비 (Fork 전 단계)

이 매뉴얼은 아래 항목이 완료된 상태를 전제합니다:

- [x] WordPress 사이트 설치 완료 (Cloudways 등)
- [x] 도메인 연결 + SSL(HTTPS) 적용
- [x] GitHub 계정 생성 + `planxs-ai/wp-auto` Fork 완료
- [x] Fork한 저장소에서 **Actions 탭 → "I understand my workflows, go ahead and enable them"** 클릭

---

## STEP 1. 워드프레스 앱 비밀번호 생성

AutoBlog이 글을 발행하려면 워드프레스 **앱 비밀번호**(Application Password)가 필요합니다.

1. 워드프레스 관리자 로그인 (`내블로그.com/wp-admin`)
2. 좌측 메뉴 → **사용자** → **프로필**
3. 페이지 맨 아래 **"앱 비밀번호"** 섹션
4. 새 앱 비밀번호 이름: `AutoBlog` 입력
5. **"새 앱 비밀번호 추가"** 클릭
6. 생성된 비밀번호를 **반드시 복사하여 메모** (다시 볼 수 없음!)

```
형식 예시: ABCD 1234 EFGH 5678 IJKL 9012 (공백 포함 그대로 사용)
```

> **앱 비밀번호가 안 보인다면?**
> - WordPress 5.6 이상인지 확인
> - HTTPS가 적용되어 있는지 확인 (http://에서는 앱 비밀번호 사용 불가)

---

## STEP 2. Gemini API 키 발급

AI 글 작성 엔진으로 사용할 Google Gemini API 키를 발급합니다. **무료** 로 하루 1,500회 요청 가능합니다.

1. [Google AI Studio](https://aistudio.google.com) 접속 (Google 계정 로그인)
2. 좌측 메뉴 → **"Get API key"**
3. **"Create API key"** 클릭
4. 프로젝트 선택 (기본 프로젝트 OK)
5. 생성된 API 키 복사하여 메모

```
형식 예시: AIzaSyA-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## STEP 3. Supabase 프로젝트 생성

발행 기록, 사용자 인증, 설정 데이터를 저장할 데이터베이스입니다.

### 3-1. 프로젝트 생성

1. [supabase.com](https://supabase.com) 접속 → **GitHub 계정으로 로그인**
2. **"New project"** 클릭
3. 입력:
   - **Organization:** 기본 조직 선택
   - **Project name:** `my-autoblog` (원하는 이름)
   - **Database Password:** 강력한 비밀번호 → 메모
   - **Region:** `Northeast Asia (ap-northeast-1)` (한국과 가장 가까움)
4. **"Create new project"** 클릭 → 약 2분 소요

### 3-2. API 키 확인

프로젝트 대시보드 → **Settings** → **API** 에서 아래 3개 값을 메모합니다:

| 항목 | 위치 | 용도 |
|------|------|------|
| **Project URL** | API Settings 상단 | 데이터베이스 주소 |
| **anon/public key** | Project API keys | 프론트엔드(대시보드) 접근용 |
| **service_role key** | Project API keys | 백엔드(발행 엔진) 접근용 |

> **service_role key는 절대 프론트엔드에 노출하지 마세요!** GitHub Secrets에만 저장합니다.

### 3-3. 데이터베이스 테이블 생성

Fork한 저장소의 `migrations/` 폴더에 SQL 파일이 있습니다.

1. Supabase 대시보드 → **SQL Editor** 클릭
2. **`migrations/001_consumer_dashboard.sql`** 내용을 복사 → 붙여넣기 → **Run**

> 이 SQL은 다음 테이블을 생성합니다:
> - `plans` — 요금제 (Standard/Premium/MaMa)
> - `user_profiles` — 사용자 프로필 (auth.users 확장)
> - `user_sites` — 사용자-사이트 매핑
> - `user_milestones` — 마일스톤 추적
> - RLS 정책 + 자동 프로필 생성 트리거

**주의:** `001` 마이그레이션에서 `sites` 테이블을 참조하므로, `sites` 테이블이 아직 없다면 먼저 생성해야 합니다. 기존에 `sites` 테이블이 있는 경우 그대로 진행하세요.

### 3-4. 인증 설정

1. Supabase → **Authentication** → **Providers** → **Email** 활성화 (기본값)
2. **Authentication** → **URL Configuration**:
   - **Site URL:** `https://내대시보드.vercel.app` (Vercel 배포 후 업데이트)
   - **Redirect URLs:** `https://내대시보드.vercel.app/**` 추가

---

## STEP 4. Vercel 배포 (대시보드)

대시보드를 인터넷에 공개하여 어디서든 접속할 수 있게 합니다.

### 4-1. Vercel 가입 + Import

1. [vercel.com](https://vercel.com) → **GitHub 계정으로 가입**
2. **"Add New..."** → **"Project"**
3. **"Import Git Repository"** 에서 Fork한 `wp-auto` 저장소 선택
4. Framework: **Next.js** (자동 감지)

### 4-2. 환경변수 설정 (중요!)

Deploy 전에 **"Environment Variables"** 섹션에서 아래 변수를 추가합니다:

| Key | Value | 설명 |
|-----|-------|------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase Project URL | 대시보드 DB 연결 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | 대시보드 인증 |
| `GITHUB_TOKEN` | GitHub Personal Access Token | 대시보드에서 워크플로우 트리거 |
| `GITHUB_REPO` | `내계정/wp-auto` | Fork한 저장소 경로 |

> **GITHUB_TOKEN, GITHUB_REPO가 없으면** 대시보드 설정 페이지의 "메뉴 설정", "CSS 주입", "첫 발행" 버튼이 작동하지 않습니다!

### 4-3. GitHub Personal Access Token 생성

1. GitHub → 우측 상단 프로필 → **Settings**
2. 좌측 맨 아래 → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
3. **"Generate new token"** 클릭
4. 설정:
   - **Token name:** `AutoBlog Dashboard`
   - **Expiration:** 90일 또는 1년
   - **Repository access:** "Only select repositories" → Fork한 `wp-auto` 선택
   - **Permissions → Repository permissions:**
     - **Actions:** Read and write (워크플로우 실행에 필요)
     - **Contents:** Read and write (코드 접근에 필요)
5. **"Generate token"** → 복사하여 Vercel에 `GITHUB_TOKEN`으로 저장

### 4-4. Deploy

1. **"Deploy"** 클릭 → 1~2분 후 배포 완료
2. 배포된 URL 확인 (예: `my-autoblog.vercel.app`)

### 4-5. Supabase 리다이렉트 URL 업데이트

배포 URL이 확정되면 Supabase로 돌아가서:

1. **Authentication** → **URL Configuration**
2. **Site URL:** `https://내대시보드.vercel.app`
3. **Redirect URLs:** `https://내대시보드.vercel.app/**` 추가

---

## STEP 5. GitHub Secrets 설정 (자동 발행용)

GitHub Actions가 매일 자동으로 글을 발행하려면 API 키들을 안전하게 저장해야 합니다.

### 설정 방법

1. Fork한 저장소 → **Settings** 탭
2. 좌측 → **Secrets and variables** → **Actions**
3. **"New repository secret"** 클릭하여 아래 항목을 하나씩 추가

### 필수 Secrets

| Name | Value | 어디서 얻나? |
|------|-------|-------------|
| `GEMINI_API_KEY` | Gemini API 키 | STEP 2에서 발급 |
| `SUPABASE_URL` | Supabase Project URL | STEP 3에서 확인 |
| `SUPABASE_KEY` | Supabase **service_role** key | STEP 3에서 확인 |

> **WP_URL, WP_USERNAME, WP_APP_PASSWORD는?**
> 대시보드 온보딩에서 입력한 WP 인증정보가 Supabase `sites.config`에 저장되고,
> 대시보드에서 워크플로우 트리거 시 자동으로 전달됩니다.
> GitHub Secrets에도 설정하면 **스케줄 자동 발행** (cron)에서도 사용됩니다.

### 스케줄 자동 발행용 Secrets (권장)

대시보드 수동 트리거가 아닌, cron 스케줄(하루 4회)로 자동 발행하려면 추가 설정:

| Name | Value |
|------|-------|
| `WP_URL` | 워드프레스 주소 (예: `https://myblog.com`) |
| `WP_USERNAME` | 워드프레스 로그인 ID |
| `WP_APP_PASSWORD` | STEP 1에서 생성한 앱 비밀번호 |

### 선택 Secrets (나중에 추가 가능)

| Name | 용도 | 비용 |
|------|------|------|
| `UNSPLASH_ACCESS_KEY` | 무료 이미지 자동 삽입 | 무료 |
| `PEXELS_API_KEY` | 대체 이미지 소스 | 무료 |
| `PIXABAY_API_KEY` | 대체 이미지 소스 | 무료 |
| `CLAUDE_API_KEY` | AI 폴리싱 (고급) | 유료 |
| `DEEPSEEK_API_KEY` | 대체 AI 모델 | 유료 |
| `TELEGRAM_BOT_TOKEN` | 발행 알림 | 무료 |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅방 ID | 무료 |

---

## STEP 6. 대시보드 가입 + 온보딩

이제 배포된 대시보드에 접속하여 초기 설정을 진행합니다.

### 6-1. 회원가입

1. `https://내대시보드.vercel.app/login` 접속
2. **"회원가입"** 탭 클릭
3. 이름, 이메일, 비밀번호 입력 → **"회원가입"** 클릭
4. 가입 즉시 대시보드로 이동 (7일 Premium 무료 체험 시작)

### 6-2. 온보딩 5단계

가입 후 자동으로 온보딩 화면이 나타납니다:

**Step 1: 워드프레스 연결**

| 입력 항목 | 예시 |
|-----------|------|
| 사이트 URL | `https://myblog.com` |
| 사용자명 | 워드프레스 로그인 ID |
| 앱 비밀번호 | STEP 1에서 복사한 비밀번호 |

- **"연결 테스트"** 버튼으로 성공 확인 후 다음 진행
- 연결 성공 시 Supabase `sites` 테이블에 사이트가 자동 등록됩니다

**Step 2: 카테고리 선택 (최소 2개)**

인기 조합 추천:

| 조합 | 특징 |
|------|------|
| AI 도구 + 재테크 | 수익화 ROI 최고 |
| 스마트홈 + 가전 | 쿠팡 연동 유리 |
| 건강 + 뷰티 | 텐핑 CPA 전환율 높음 |
| 정부지원 + 세금 | 검색량 안정적 |

**Step 3: 발행 스케줄 선택**

| 옵션 | 시간 | 추천 |
|------|------|------|
| 하루 2회 | 08:00, 18:00 | 초보자 |
| 하루 4회 | 07:00, 12:00, 17:00, 22:00 | 빠른 성장 |
| 평일 1회 | 08:00 (월~금) | 보수적 운영 |

**Step 4: 블로그 단계 선택**

| 단계 | 선택 기준 |
|------|-----------|
| 신규 블로그 | 글이 거의 없는 새 블로그 |
| 애드센스 준비 중 | 글은 있지만 애드센스 미승인 |
| 애드센스 승인 완료 | 애드센스 수익 발생 중 |
| 수익화 단계 | 다채널 수익 운영 중 |

**Step 5: 설정 확인 → "시작하기" 클릭**

---

## STEP 7. 초기 블로그 세팅 (설정 페이지)

온보딩 완료 후 대시보드의 **설정** 페이지에서 4가지 초기 작업을 **순서대로** 실행합니다.

| 순서 | 버튼 | 역할 | 소요시간 |
|------|------|------|----------|
| 1 | **메뉴 자동 설정** | 니치 기반 카테고리 + 네비게이션 메뉴 생성 | 1~2분 |
| 2 | **필수 페이지 생성** | About, Privacy Policy 등 애드센스 필수 페이지 | 1~2분 |
| 3 | **모바일 CSS 적용** | 블로그 테마 반응형 스타일링 | 1~2분 |
| 4 | **첫 글 발행** | AI가 선택한 니치로 글 3편 자동 발행 | 5~10분 |

> **4개 모두 반드시 순서대로 실행하세요!**
> - 메뉴 설정 → 워드프레스에 카테고리와 네비게이션이 생성됩니다
> - 필수 페이지 → 애드센스 승인에 필요한 소개/개인정보/연락처 페이지가 생성됩니다
> - CSS 적용 → 모바일에서 보기 좋은 디자인이 적용됩니다
> - 첫 발행 → AI가 실제로 글을 작성하여 워드프레스에 발행합니다

### 실행 확인

각 버튼 클릭 후:
1. GitHub → Fork한 저장소 → **Actions** 탭에서 워크플로우 실행 상태 확인
2. 초록 체크(✓)가 나오면 성공
3. 빨간 X가 나오면 → 클릭하여 에러 로그 확인

---

## STEP 8. 자동 발행 확인 + 운영

### 자동 발행 스케줄

GitHub Actions가 매일 4회 자동으로 글을 발행합니다:

| 시간 (KST) | cron (UTC) | 비고 |
|------------|------------|------|
| 07:00 | `0 22 * * *` | 출근길 |
| 12:00 | `0 3 * * *` | 점심 |
| 17:00 | `0 8 * * *` | 퇴근길 |
| 22:00 | `0 13 * * *` | 야간 |

> **스케줄 변경:** `.github/workflows/publish.yml`의 cron 값을 수정하세요.

### 발행 확인 방법

1. **워드프레스:** `내블로그.com/wp-admin` → 글 목록에서 새 글 확인
2. **대시보드:** 홈 화면에서 오늘 발행 수, 품질 점수 확인
3. **GitHub:** Actions 탭에서 워크플로우 실행 기록 확인

### 대시보드 메뉴

| 메뉴 | 기능 |
|------|------|
| **홈** | 발행 현황, 수익, 건강 점수 한눈에 |
| **내 블로그** | 발행된 글 목록, 품질 점수, 카테고리 분포 |
| **수익** | 월별 수익 추이, 채널별 비교 |
| **설정** | 카테고리 변경, 스케줄 수정, 세팅 재실행 |

---

## 수익화 로드맵

```
[1단계] 콘텐츠 축적 (1~2주)     [2단계] 수익 시작 (2~4주)      [3단계] 수익 극대화 (1개월+)
━━━━━━━━━━━━━━━━━━━━━        ━━━━━━━━━━━━━━━━━━━         ━━━━━━━━━━━━━━━━━━━━
• 매일 자동 발행 → 20편 축적     • 애드센스 승인 → 자동 광고      • 쿠팡 API 자동화
• 설정에서 메뉴/CSS/페이지 실행   • 텐핑 CPA (건당 3~8천원)      • 고RPM 카테고리 비중 확대
• 20편 쌓이면 애드센스 신청       • 쿠팡 수동 링크 삽입           • 목표: 월 30만원+ 자동 수익
```

### 현실적 수익 기대치

| 기간 | 예상 수익 | 핵심 활동 |
|------|----------|----------|
| 1개월 | 월 1~3만원 | 애드센스 승인 + 초기 트래픽 |
| 2개월 | 월 5~15만원 | 텐핑/쿠팡 추가 |
| 3개월+ | 월 20~50만원 | 자동화 안정화 |

---

## 트러블슈팅

### 대시보드 관련

| 증상 | 원인 | 해결 |
|------|------|------|
| 로그인 안 됨 | Supabase 환경변수 오류 | Vercel의 `NEXT_PUBLIC_SUPABASE_*` 확인 |
| 설정 버튼이 안 눌림 | GITHUB_TOKEN 미설정 | Vercel에 `GITHUB_TOKEN`, `GITHUB_REPO` 추가 |
| 온보딩 WP 연결 실패 | 앱 비밀번호 오류 | 일반 비밀번호가 아닌 **앱 비밀번호** 사용 확인 |
| 가입은 되는데 프로필 안 생김 | 마이그레이션 누락 | `001_consumer_dashboard.sql` 실행 확인 |

### 자동 발행 관련

| 증상 | 원인 | 해결 |
|------|------|------|
| Actions 빨간 X | Secrets 누락/오타 | Settings → Secrets에서 값 재확인 |
| WP 연결 실패 | 앱 비밀번호 오류 | `WP_APP_PASSWORD` 공백 포함 여부 확인 |
| Gemini API 에러 | API 키 오류/미활성 | Google AI Studio에서 키 재생성 |
| 글 발행 성공인데 DB 기록 없음 | Supabase 키 오류 | `SUPABASE_URL`, `SUPABASE_KEY` 확인 |
| 스케줄은 돌지만 글이 안 써짐 | AI 모델 키 전부 누락 | 최소 `GEMINI_API_KEY` 필요 |

### 에러 로그 확인 방법

1. Fork한 저장소 → **Actions** 탭
2. 실패한 워크플로우 클릭
3. 빨간 X가 표시된 단계 클릭 → 상세 로그 확인

---

## 전체 체크리스트

```
[ ] STEP 1. 워드프레스 앱 비밀번호 생성
[ ] STEP 2. Gemini API 키 발급 (Google AI Studio)
[ ] STEP 3. Supabase 프로젝트 생성
    [ ] 3-1. 프로젝트 생성 + API 키 메모
    [ ] 3-2. SQL Editor에서 마이그레이션 실행
    [ ] 3-3. Authentication → Email 활성화
[ ] STEP 4. Vercel 배포
    [ ] 4-1. GitHub 연동 + 저장소 Import
    [ ] 4-2. 환경변수 4개 설정 (SUPABASE_URL, ANON_KEY, GITHUB_TOKEN, GITHUB_REPO)
    [ ] 4-3. Deploy 완료
    [ ] 4-4. Supabase Redirect URL 업데이트
[ ] STEP 5. GitHub Secrets 설정
    [ ] 5-1. 필수: GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
    [ ] 5-2. 권장: WP_URL, WP_USERNAME, WP_APP_PASSWORD
[ ] STEP 6. 대시보드 가입 + 온보딩
    [ ] 6-1. 회원가입
    [ ] 6-2. 온보딩 5단계 완료
[ ] STEP 7. 초기 블로그 세팅
    [ ] 7-1. 메뉴 자동 설정
    [ ] 7-2. 필수 페이지 생성
    [ ] 7-3. 모바일 CSS 적용
    [ ] 7-4. 첫 글 발행
[ ] STEP 8. 자동 발행 확인
    [ ] 8-1. 워드프레스에서 글 확인
    [ ] 8-2. 대시보드에서 발행 현황 확인
```

---

## FAQ

### Q. 코딩을 전혀 모르는데 가능한가요?
모든 단계가 클릭과 복사-붙여넣기만으로 완료됩니다. 약 30~40분이면 전체 설정이 끝납니다.

### Q. 월 비용이 얼마인가요?
Cloudways 호스팅비 약 15,000원($11)/월이 전부입니다. Gemini, GitHub, Supabase, Vercel 모두 무료입니다.

### Q. Fork 후 업데이트는 어떻게 받나요?
GitHub에서 **"Sync fork"** → **"Update branch"** 클릭 한 번이면 됩니다. Vercel이 자동 재배포합니다.

### Q. 여러 블로그를 운영할 수 있나요?
네. Fork를 여러 개 만들거나, 하나의 Fork에서 환경변수를 바꿔가며 운영할 수 있습니다.

### Q. GitHub Actions 무료 한도가 걱정됩니다.
무료 계정은 월 2,000분입니다. 하루 4회 발행(회당 약 5분) = 월 600분이므로 넉넉합니다.

### Q. 애드센스 승인이 안 됩니다.
20편 이상 + 필수 페이지(소개/개인정보/연락처) + HTTPS + "검색엔진 색인 허용" 확인하세요. 설정에서 메뉴/페이지 세팅을 실행하면 필수 페이지가 자동 생성됩니다.

### Q. 워드프레스 연결이 안 됩니다.
1. URL에 `https://` 포함 확인
2. **앱 비밀번호**를 사용했는지 확인 (일반 비밀번호 아님!)
3. WordPress 5.6 이상인지 확인
4. 보안 플러그인(Wordfence 등)이 REST API를 차단하지 않는지 확인

---

## 문의

설치 중 막히는 부분이 있으면: **planxsol@gmail.com**

---

*AutoBlog — AI가 글을 쓰고, 당신은 수익을 거둡니다.*
