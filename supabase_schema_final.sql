-- ============================================================
-- AutoBlog 통합 대시보드 — Supabase Schema v3.0
-- 10블로그 스케일, RLS 활성화, 인덱스 최적화
-- ============================================================
-- 실행: Supabase Dashboard → SQL Editor → 붙여넣기 → Run
-- ============================================================

-- 1. 사이트(블로그) 마스터
CREATE TABLE IF NOT EXISTS sites (
    id TEXT PRIMARY KEY,                      -- 'site-1', 'site-2', ...
    name TEXT NOT NULL,                       -- '신줌AI 재테크'
    domain TEXT NOT NULL,                     -- 'sinjum-ai.com'
    wp_url TEXT,                              -- 'https://sinjum-ai.com/wp-json/wp/v2'
    niche TEXT DEFAULT 'finance',             -- 'finance', 'tech', 'health'
    status TEXT DEFAULT 'active',             -- 'active', 'paused', 'archived'
    daily_target INT DEFAULT 10,              -- 일 발행 목표
    config JSONB DEFAULT '{}'::jsonb,         -- 사이트별 설정 (API키 제외)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 발행 로그
CREATE TABLE IF NOT EXISTS publish_logs (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT REFERENCES sites(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT,
    keyword TEXT,
    intent TEXT,                              -- 'informational', 'transactional'
    category TEXT,
    pipeline TEXT DEFAULT 'autoblog',         -- 'autoblog', 'hotdeal', 'promo'
    hook_id TEXT,
    content_length INT DEFAULT 0,
    has_image BOOLEAN DEFAULT FALSE,
    image_tier TEXT,
    has_coupang BOOLEAN DEFAULT FALSE,
    has_tenping BOOLEAN DEFAULT FALSE,
    has_email_cta BOOLEAN DEFAULT FALSE,
    sns_shared JSONB DEFAULT '[]'::jsonb,     -- ['pinterest', 'facebook', 'x']
    seo_indexed BOOLEAN DEFAULT FALSE,
    cluster_id TEXT,
    cannibal_score FLOAT DEFAULT 0,
    status TEXT DEFAULT 'published',          -- 'published', 'failed', 'dry_run'
    error_message TEXT,
    published_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. API 비용 추적
CREATE TABLE IF NOT EXISTS api_costs (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT REFERENCES sites(id) ON DELETE CASCADE,
    model TEXT NOT NULL,                      -- 'deepseek-chat', 'claude-haiku-4-5'
    provider TEXT,                            -- 'deepseek', 'anthropic', 'openai'
    purpose TEXT,                             -- 'content', 'title', 'image', 'polish'
    tokens_input INT DEFAULT 0,
    tokens_output INT DEFAULT 0,
    cost_usd FLOAT DEFAULT 0,
    cost_krw INT DEFAULT 0,
    pipeline TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 수익 추적
CREATE TABLE IF NOT EXISTS revenue (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT REFERENCES sites(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,                    -- 'adsense', 'coupang_cps', 'tenping_cpa'
    date DATE NOT NULL,
    impressions INT DEFAULT 0,
    clicks INT DEFAULT 0,
    conversions INT DEFAULT 0,
    revenue_krw INT DEFAULT 0,
    revenue_usd FLOAT DEFAULT 0,
    details JSONB DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(site_id, channel, date)
);

-- 5. SEO 현황
CREATE TABLE IF NOT EXISTS seo_health (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT REFERENCES sites(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_posts INT DEFAULT 0,
    indexed_posts INT DEFAULT 0,
    indexing_rate FLOAT DEFAULT 0,
    broken_links INT DEFAULT 0,
    cannibal_warnings INT DEFAULT 0,
    avg_position FLOAT,
    total_impressions INT DEFAULT 0,
    total_clicks INT DEFAULT 0,
    top_keywords JSONB DEFAULT '[]'::jsonb,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(site_id, date)
);

-- 6. 이메일 구독 현황
CREATE TABLE IF NOT EXISTS email_stats (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT REFERENCES sites(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_subscribers INT DEFAULT 0,
    new_subscribers INT DEFAULT 0,
    unsubscribed INT DEFAULT 0,
    conversion_rate FLOAT DEFAULT 0,
    newsletters_sent INT DEFAULT 0,
    open_rate FLOAT DEFAULT 0,
    click_rate FLOAT DEFAULT 0,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(site_id, date)
);

-- 7. SNS 성과
CREATE TABLE IF NOT EXISTS sns_stats (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT REFERENCES sites(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,                   -- 'pinterest', 'facebook', 'x'
    date DATE NOT NULL,
    posts_shared INT DEFAULT 0,
    impressions INT DEFAULT 0,
    clicks INT DEFAULT 0,
    followers INT DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(site_id, platform, date)
);

-- 8. 알림/이벤트 로그
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    site_id TEXT REFERENCES sites(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,                 -- 'publish_fail', 'revenue_drop', 'cost_spike'
    severity TEXT DEFAULT 'warning',          -- 'info', 'warning', 'critical'
    title TEXT NOT NULL,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. 대시보드 설정 (GitHub Actions 연동)
CREATE TABLE IF NOT EXISTS dashboard_config (
    id TEXT PRIMARY KEY DEFAULT 'global',
    settings JSONB DEFAULT '{}'::jsonb,       -- 전역 설정
    site_configs JSONB DEFAULT '{}'::jsonb,   -- 사이트별 설정 오버라이드
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 인덱스
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_publish_site_date ON publish_logs(site_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_publish_pipeline ON publish_logs(pipeline, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_publish_status ON publish_logs(status, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_costs_site_date ON api_costs(site_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_costs_model ON api_costs(model, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_site_date ON revenue(site_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_channel ON revenue(channel, date DESC);
CREATE INDEX IF NOT EXISTS idx_seo_site_date ON seo_health(site_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_unread ON alerts(is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sns_site_platform ON sns_stats(site_id, platform, date DESC);

-- ============================================================
-- RLS (Row Level Security) — anon 키로 읽기/쓰기 허용
-- 프로덕션에서는 서비스 롤 키 + 인증으로 강화할 것
-- ============================================================
ALTER TABLE sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE publish_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_costs ENABLE ROW LEVEL SECURITY;
ALTER TABLE revenue ENABLE ROW LEVEL SECURITY;
ALTER TABLE seo_health ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE sns_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_config ENABLE ROW LEVEL SECURITY;

-- 개발용: anon 키로 모든 작업 허용 (나중에 인증 추가 시 변경)
CREATE POLICY "Allow all for anon" ON sites FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON publish_logs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON api_costs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON revenue FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON seo_health FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON email_stats FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON sns_stats FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON alerts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for anon" ON dashboard_config FOR ALL USING (true) WITH CHECK (true);

-- ============================================================
-- 초기 데이터: 첫 번째 사이트 등록
-- ============================================================
INSERT INTO sites (id, name, domain, wp_url, niche, daily_target)
VALUES ('site-1', '신줌AI 재테크', 'sinjum-ai.com', 'https://sinjum-ai.com/wp-json/wp/v2', 'finance', 10)
ON CONFLICT (id) DO NOTHING;

-- 글로벌 설정 초기화
INSERT INTO dashboard_config (id, settings)
VALUES ('global', '{
    "daily_post_target": 10,
    "cost_alert_threshold_krw": 5000,
    "revenue_drop_alert_pct": 20,
    "auto_pause_on_error_count": 5,
    "timezone": "Asia/Seoul"
}'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- 뷰: 자주 쓰는 집계 쿼리
-- ============================================================

-- 오늘 발행 현황
CREATE OR REPLACE VIEW v_today_stats AS
SELECT
    s.id AS site_id,
    s.name AS site_name,
    s.daily_target,
    COUNT(pl.id) FILTER (WHERE pl.status = 'published' AND pl.published_at::date = CURRENT_DATE) AS today_posts,
    COUNT(pl.id) FILTER (WHERE pl.status = 'failed' AND pl.published_at::date = CURRENT_DATE) AS today_failures,
    COALESCE(SUM(ac.cost_krw) FILTER (WHERE ac.recorded_at::date = CURRENT_DATE), 0) AS today_cost_krw
FROM sites s
LEFT JOIN publish_logs pl ON s.id = pl.site_id
LEFT JOIN api_costs ac ON s.id = ac.site_id
WHERE s.status = 'active'
GROUP BY s.id, s.name, s.daily_target;

-- 월간 수익 요약
CREATE OR REPLACE VIEW v_monthly_revenue AS
SELECT
    site_id,
    channel,
    DATE_TRUNC('month', date) AS month,
    SUM(revenue_krw) AS total_krw,
    SUM(revenue_usd) AS total_usd,
    SUM(clicks) AS total_clicks,
    SUM(conversions) AS total_conversions
FROM revenue
GROUP BY site_id, channel, DATE_TRUNC('month', date);

-- 사이트별 ROI (수익 - API 비용)
CREATE OR REPLACE VIEW v_site_roi AS
SELECT
    s.id AS site_id,
    s.name,
    COALESCE(r.month_revenue, 0) AS month_revenue_krw,
    COALESCE(c.month_cost, 0) AS month_cost_krw,
    COALESCE(r.month_revenue, 0) - COALESCE(c.month_cost, 0) AS month_profit_krw,
    CASE WHEN COALESCE(c.month_cost, 0) > 0
        THEN ROUND(((COALESCE(r.month_revenue, 0) - COALESCE(c.month_cost, 0))::numeric / c.month_cost * 100)::numeric, 1)
        ELSE 0 END AS roi_pct
FROM sites s
LEFT JOIN (
    SELECT site_id, SUM(revenue_krw) AS month_revenue
    FROM revenue
    WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY site_id
) r ON s.id = r.site_id
LEFT JOIN (
    SELECT site_id, SUM(cost_krw) AS month_cost
    FROM api_costs
    WHERE recorded_at >= DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY site_id
) c ON s.id = c.site_id
WHERE s.status = 'active';
