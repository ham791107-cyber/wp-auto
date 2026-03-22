'use client';
import { useState } from 'react';
import { useSites, useTodayStats, useRecentPosts, useMonthlyRevenue, useMonthlyCosts, useAlerts, usePublishTrend } from '@/lib/hooks';
import { supabase, isConfigured } from '@/lib/supabase';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';

// ── 탭 목록 ──
const TABS = ['개요', '발행 로그', '수익', '비용', '알림', '설정'];

// ── 공통 컴포넌트 ──
function Card({ children, style }) {
  return (
    <div style={{
      background: 'var(--card)', border: '1px solid var(--card-border)',
      borderRadius: 12, padding: 20, ...style
    }}>
      {children}
    </div>
  );
}

function StatCard({ label, value, sub, color }) {
  return (
    <Card>
      <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color: color || 'var(--text)' }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>{sub}</div>}
    </Card>
  );
}

function Badge({ text, color }) {
  const colors = {
    green: { bg: 'rgba(52,211,153,0.15)', text: '#34d399' },
    red: { bg: 'rgba(248,113,113,0.15)', text: '#f87171' },
    yellow: { bg: 'rgba(251,191,36,0.15)', text: '#fbbf24' },
    blue: { bg: 'rgba(96,165,250,0.15)', text: '#60a5fa' },
    purple: { bg: 'rgba(139,92,246,0.15)', text: '#8b5cf6' },
  };
  const c = colors[color] || colors.blue;
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 6,
      fontSize: 11, fontWeight: 600, background: c.bg, color: c.text
    }}>{text}</span>
  );
}

function fmt(n) { return (n || 0).toLocaleString('ko-KR'); }
function fmtKRW(n) { return '₩' + fmt(n); }

// ── 메인 ──
export default function Dashboard() {
  const [tab, setTab] = useState(0);
  const [selectedSite, setSelectedSite] = useState('site-1');
  const { sites, loading: sitesLoading } = useSites();

  if (!isConfigured) {
    return <SetupGuide />;
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* 헤더 */}
      <header style={{
        background: 'linear-gradient(180deg, rgba(139,92,246,0.08) 0%, transparent 100%)',
        borderBottom: '1px solid var(--card-border)', padding: '20px 24px 0'
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <h1 style={{ fontSize: 24, fontWeight: 900, letterSpacing: -0.5 }}>
                <span style={{ color: 'var(--accent-light)' }}>AutoBlog</span> Dashboard
              </h1>
              <p style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 2 }}>
                수익 자동화 통합 대시보드 · {sites.length}개 사이트
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <select
                value={selectedSite}
                onChange={(e) => setSelectedSite(e.target.value)}
                style={{
                  background: 'var(--card)', border: '1px solid var(--card-border)',
                  borderRadius: 8, padding: '6px 12px', color: 'var(--text)', fontSize: 13
                }}
              >
                {sites.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--green)', animation: 'pulse 2s infinite' }} />
                <span style={{ fontSize: 12, color: 'var(--green)', fontWeight: 600 }}>연결됨</span>
              </div>
            </div>
          </div>

          {/* 탭 */}
          <div style={{ display: 'flex', gap: 2, overflowX: 'auto' }}>
            {TABS.map((t, i) => (
              <button key={t} onClick={() => setTab(i)} style={{
                padding: '10px 18px', border: 'none', borderRadius: '10px 10px 0 0',
                cursor: 'pointer', fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap',
                background: tab === i ? 'rgba(139,92,246,0.15)' : 'transparent',
                color: tab === i ? 'var(--accent-light)' : 'var(--text-dim)',
                borderBottom: tab === i ? '2px solid var(--accent)' : '2px solid transparent'
              }}>{t}</button>
            ))}
          </div>
        </div>
      </header>

      {/* 콘텐츠 */}
      <main style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 24px 48px' }}>
        {tab === 0 && <OverviewTab siteId={selectedSite} />}
        {tab === 1 && <PostsTab siteId={selectedSite} />}
        {tab === 2 && <RevenueTab siteId={selectedSite} />}
        {tab === 3 && <CostsTab siteId={selectedSite} />}
        {tab === 4 && <AlertsTab siteId={selectedSite} />}
        {tab === 5 && <SettingsTab siteId={selectedSite} sites={sites} />}
      </main>
    </div>
  );
}

// ── 개요 탭 ──
function OverviewTab({ siteId }) {
  const { stats } = useTodayStats(siteId);
  const { total: rev } = useMonthlyRevenue(siteId);
  const { costs } = useMonthlyCosts(siteId);
  const { trend } = usePublishTrend(siteId, 7);
  const { alerts } = useAlerts(siteId);

  const unread = alerts.filter(a => !a.is_read).length;
  const profit = rev.krw - costs.total_krw;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* KPI 카드 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        <StatCard label="오늘 발행" value={`${stats.posts}편`} sub={stats.failures > 0 ? `${stats.failures}건 실패` : '전체 성공'} color="var(--accent-light)" />
        <StatCard label="이번 달 수익" value={fmtKRW(rev.krw)} sub={rev.usd > 0 ? `$${rev.usd.toFixed(2)}` : ''} color="var(--green)" />
        <StatCard label="이번 달 비용" value={fmtKRW(costs.total_krw)} color="var(--yellow)" />
        <StatCard label="순이익" value={fmtKRW(profit)} sub={costs.total_krw > 0 ? `ROI ${((profit / costs.total_krw) * 100).toFixed(0)}%` : ''} color={profit >= 0 ? 'var(--green)' : 'var(--red)'} />
      </div>

      {/* 차트 + 알림 */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>7일 발행 추이</div>
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                <Bar dataKey="published" fill="#8b5cf6" radius={[4, 4, 0, 0]} name="발행" />
                <Bar dataKey="failed" fill="#f87171" radius={[4, 4, 0, 0]} name="실패" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)', fontSize: 13 }}>
              데이터 수집 중... GitHub Actions 발행 후 자동 반영됩니다.
            </div>
          )}
        </Card>

        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: 14, fontWeight: 700 }}>알림</span>
            {unread > 0 && <Badge text={`${unread}건`} color="red" />}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 200, overflowY: 'auto' }}>
            {alerts.slice(0, 5).map(a => (
              <div key={a.id} style={{
                padding: '8px 10px', borderRadius: 8,
                background: a.is_read ? 'transparent' : 'rgba(139,92,246,0.05)',
                border: '1px solid var(--card-border)', fontSize: 12
              }}>
                <div style={{ fontWeight: 600, color: a.severity === 'critical' ? 'var(--red)' : 'var(--text)' }}>
                  {a.title}
                </div>
                <div style={{ color: 'var(--text-dim)', marginTop: 2 }}>{a.message?.slice(0, 60)}</div>
              </div>
            ))}
            {alerts.length === 0 && (
              <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-dim)', fontSize: 13 }}>알림 없음</div>
            )}
          </div>
        </Card>
      </div>

      {/* 모델별 비용 파이 */}
      {Object.keys(costs.by_model).length > 0 && (
        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>모델별 비용 분포</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <ResponsiveContainer width={180} height={180}>
              <PieChart>
                <Pie
                  data={Object.entries(costs.by_model).map(([name, value]) => ({ name, value }))}
                  cx="50%" cy="50%" innerRadius={50} outerRadius={75}
                  dataKey="value" paddingAngle={2}
                >
                  {Object.keys(costs.by_model).map((_, i) => (
                    <Cell key={i} fill={['#8b5cf6', '#60a5fa', '#34d399', '#fbbf24', '#f87171'][i % 5]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => fmtKRW(v)} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {Object.entries(costs.by_model).sort((a, b) => b[1] - a[1]).map(([model, cost], i) => (
                <div key={model} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 2, background: ['#8b5cf6', '#60a5fa', '#34d399', '#fbbf24', '#f87171'][i % 5] }} />
                  <span style={{ fontSize: 12, color: 'var(--text-dim)', minWidth: 120 }}>{model}</span>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>{fmtKRW(cost)}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

// ── 발행 로그 탭 ──
function PostsTab({ siteId }) {
  const { posts, loading } = useRecentPosts(siteId, 50);

  return (
    <Card>
      <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>최근 발행 ({posts.length}건)</div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
              {['시간', '제목', '파이프라인', '키워드', '길이', '이미지', '쿠팡', 'SNS', '상태'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '8px 6px', color: 'var(--text-dim)', fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {posts.map(p => (
              <tr key={p.id} style={{ borderBottom: '1px solid var(--card-border)' }}>
                <td style={{ padding: '8px 6px', whiteSpace: 'nowrap', color: 'var(--text-dim)' }}>
                  {new Date(p.published_at).toLocaleString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                </td>
                <td style={{ padding: '8px 6px', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {p.url ? <a href={p.url} target="_blank" rel="noopener" style={{ color: 'var(--accent-light)', textDecoration: 'none' }}>{p.title}</a> : p.title}
                </td>
                <td style={{ padding: '8px 6px' }}><Badge text={p.pipeline} color="purple" /></td>
                <td style={{ padding: '8px 6px', color: 'var(--text-dim)' }}>{p.keyword?.slice(0, 20)}</td>
                <td style={{ padding: '8px 6px' }}>{fmt(p.content_length)}</td>
                <td style={{ padding: '8px 6px' }}>{p.has_image ? '✅' : '—'}</td>
                <td style={{ padding: '8px 6px' }}>{p.has_coupang ? '✅' : '—'}</td>
                <td style={{ padding: '8px 6px' }}>
                  {(p.sns_shared || []).map(s => <Badge key={s} text={s} color="blue" />)}
                </td>
                <td style={{ padding: '8px 6px' }}>
                  <Badge text={p.status} color={p.status === 'published' ? 'green' : p.status === 'failed' ? 'red' : 'yellow'} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-dim)' }}>로딩 중...</div>}
        {!loading && posts.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)' }}>발행 로그가 없습니다. GitHub Actions 발행 후 자동 기록됩니다.</div>
        )}
      </div>
    </Card>
  );
}

// ── 수익 탭 ──
function RevenueTab({ siteId }) {
  const { revenue, total } = useMonthlyRevenue(siteId);

  // 채널별 집계
  const byChannel = {};
  revenue.forEach(r => {
    if (!byChannel[r.channel]) byChannel[r.channel] = 0;
    byChannel[r.channel] += r.revenue_krw || 0;
  });

  // 일별 추이
  const byDate = {};
  revenue.forEach(r => {
    if (!byDate[r.date]) byDate[r.date] = { date: r.date, total: 0 };
    byDate[r.date].total += r.revenue_krw || 0;
  });
  const dailyTrend = Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date));

  const CHANNEL_COLORS = { adsense: '#34d399', coupang_cps: '#60a5fa', tenping_cpa: '#fbbf24', stibee: '#f87171', kmong: '#8b5cf6' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
        <StatCard label="이번 달 총 수익" value={fmtKRW(total.krw)} color="var(--green)" />
        {Object.entries(byChannel).map(([ch, v]) => (
          <StatCard key={ch} label={ch.replace('_', ' ').toUpperCase()} value={fmtKRW(v)} color={CHANNEL_COLORS[ch] || 'var(--blue)'} />
        ))}
      </div>

      {dailyTrend.length > 0 && (
        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>일별 수익 추이</div>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={dailyTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={v => `₩${(v/1000).toFixed(0)}k`} />
              <Tooltip formatter={(v) => fmtKRW(v)} contentStyle={{ background: '#1e1e2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
              <Line type="monotone" dataKey="total" stroke="#34d399" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {revenue.length === 0 && (
        <Card>
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)', fontSize: 13 }}>
            수익 데이터가 없습니다. report_agent.py가 수익을 수집하면 자동 반영됩니다.
          </div>
        </Card>
      )}
    </div>
  );
}

// ── 비용 탭 ──
function CostsTab({ siteId }) {
  const { costs } = useMonthlyCosts(siteId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <StatCard label="이번 달 API 비용" value={fmtKRW(costs.total_krw)} color="var(--yellow)" />

      <Card>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>모델별 비용</div>
        {Object.entries(costs.by_model).length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {Object.entries(costs.by_model).sort((a, b) => b[1] - a[1]).map(([model, cost]) => {
              const pct = costs.total_krw > 0 ? (cost / costs.total_krw * 100) : 0;
              return (
                <div key={model}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 13 }}>{model}</span>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{fmtKRW(cost)} ({pct.toFixed(1)}%)</span>
                  </div>
                  <div style={{ height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 3 }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: 'var(--accent)', borderRadius: 3 }} />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)', fontSize: 13 }}>비용 데이터 없음</div>
        )}
      </Card>
    </div>
  );
}

// ── 알림 탭 ──
function AlertsTab({ siteId }) {
  const { alerts, markRead } = useAlerts(siteId);

  const severityIcon = { critical: '🔴', warning: '🟡', info: '🟢' };

  return (
    <Card>
      <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>알림 ({alerts.length}건)</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {alerts.map(a => (
          <div key={a.id} style={{
            padding: 12, borderRadius: 8,
            background: a.is_read ? 'transparent' : 'rgba(139,92,246,0.05)',
            border: '1px solid var(--card-border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'
          }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>
                {severityIcon[a.severity] || '⚪'} {a.title}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>{a.message}</div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
                {new Date(a.created_at).toLocaleString('ko-KR')}
              </div>
            </div>
            {!a.is_read && (
              <button onClick={() => markRead(a.id)} style={{
                background: 'rgba(139,92,246,0.15)', border: 'none', borderRadius: 6,
                padding: '4px 10px', color: 'var(--accent-light)', fontSize: 11, cursor: 'pointer'
              }}>읽음</button>
            )}
          </div>
        ))}
        {alerts.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-dim)' }}>알림 없음</div>
        )}
      </div>
    </Card>
  );
}

// ── 설정 탭 ──
function SettingsTab({ siteId, sites }) {
  const site = sites.find(s => s.id === siteId);
  const [target, setTarget] = useState(site?.daily_target || 10);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    await supabase.from('sites').update({ daily_target: target, updated_at: new Date().toISOString() }).eq('id', siteId);
    setSaving(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 500 }}>
      <Card>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>사이트 설정</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 4 }}>사이트 이름</label>
            <div style={{ fontSize: 14 }}>{site?.name || '-'}</div>
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 4 }}>도메인</label>
            <div style={{ fontSize: 14 }}>{site?.domain || '-'}</div>
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-dim)', display: 'block', marginBottom: 4 }}>일일 발행 목표</label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                type="number" value={target} onChange={e => setTarget(Number(e.target.value))}
                style={{
                  background: 'var(--bg)', border: '1px solid var(--card-border)', borderRadius: 8,
                  padding: '8px 12px', color: 'var(--text)', fontSize: 14, width: 100
                }}
              />
              <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>편/일</span>
              <button onClick={save} disabled={saving} style={{
                background: 'var(--accent)', border: 'none', borderRadius: 8, padding: '8px 16px',
                color: 'white', fontSize: 13, fontWeight: 600, cursor: 'pointer', opacity: saving ? 0.5 : 1
              }}>{saving ? '저장 중...' : '저장'}</button>
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>연동 상태</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            { name: 'Supabase', status: true },
            { name: 'GitHub Actions', status: true },
            { name: 'WordPress API', status: !!site?.wp_url },
            { name: 'Google Search Console', status: false },
            { name: 'AdSense API', status: false },
          ].map(s => (
            <div key={s.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13 }}>{s.name}</span>
              <Badge text={s.status ? '연결됨' : '미연결'} color={s.status ? 'green' : 'yellow'} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ── 초기 설정 가이드 ──
function SetupGuide() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <Card style={{ maxWidth: 600, width: '100%' }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 8 }}>
          <span style={{ color: 'var(--accent-light)' }}>AutoBlog</span> Dashboard 설정
        </h2>
        <p style={{ color: 'var(--text-dim)', fontSize: 13, marginBottom: 24 }}>Supabase 연동이 필요합니다.</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>1. Supabase SQL 스키마 실행</div>
            <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
              Supabase Dashboard → SQL Editor → supabase_schema_final.sql 내용 붙여넣기 → Run
            </div>
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>2. 환경변수 설정</div>
            <div style={{
              background: 'var(--bg)', borderRadius: 8, padding: 12, fontSize: 12,
              fontFamily: 'monospace', border: '1px solid var(--card-border)'
            }}>
              <div>NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co</div>
              <div>NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key</div>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
              Vercel: Settings → Environment Variables에 위 2개 추가
            </div>
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>3. 배포</div>
            <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
              GitHub push → Vercel 자동 배포 → 대시보드 접속
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
