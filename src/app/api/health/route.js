import { NextResponse } from 'next/server';

/**
 * 시스템 환경변수 설정 상태 확인 API
 * 셀프 호스팅 사용자가 필수 설정을 빠뜨렸는지 진단용
 */
export async function GET() {
  const checks = {
    supabase_url: !!process.env.NEXT_PUBLIC_SUPABASE_URL,
    supabase_anon_key: !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    github_token: !!process.env.GITHUB_TOKEN,
    github_repo: process.env.GITHUB_REPO || null,
  };

  const github_repo_custom = !!process.env.GITHUB_REPO && process.env.GITHUB_REPO !== 'planxs-ai/wp-auto';

  return NextResponse.json({
    ok: checks.supabase_url && checks.supabase_anon_key && checks.github_token,
    checks: {
      ...checks,
      github_repo_display: process.env.GITHUB_REPO || 'planxs-ai/wp-auto (기본값)',
      github_repo_custom,
    },
    missing: Object.entries(checks).filter(([, v]) => !v).map(([k]) => k),
  });
}
