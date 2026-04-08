import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { generatePublishWorkflow } from '@/lib/workflow-template';

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_REPO = process.env.GITHUB_REPO || 'planxs-ai/wp-auto';
const WORKFLOW_PATH = '.github/workflows/publish.yml';

function getSupabaseAdmin() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );
}

async function verifyAuth(request) {
  const authHeader = request.headers.get('authorization');
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );

  if (authHeader?.startsWith('Bearer ')) {
    const token = authHeader.slice(7);
    const { data: { user }, error } = await supabase.auth.getUser(token);
    if (!error && user) return user;
  }
  return null;
}

/**
 * POST /api/schedule
 * 고객 repo의 publish.yml을 생성/업데이트
 *
 * Body: { siteId, scheduleTimes: ['08:00', '18:00'], dailyCount: 2 }
 */
export async function POST(request) {
  if (!GITHUB_TOKEN) {
    return NextResponse.json({
      error: 'GITHUB_TOKEN이 설정되지 않았습니다.',
      guide: 'Vercel 환경변수에 GITHUB_TOKEN (repo + workflow 권한)을 설정하세요.',
    }, { status: 500 });
  }

  const user = await verifyAuth(request);
  if (!user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { siteId, scheduleTimes, dailyCount } = await request.json();

  if (!siteId || !scheduleTimes || !Array.isArray(scheduleTimes) || scheduleTimes.length === 0) {
    return NextResponse.json({
      error: '사이트 ID와 스케줄 시간이 필요합니다.',
    }, { status: 400 });
  }

  // 사이트 소유권 확인
  const supabase = getSupabaseAdmin();
  const { data: userSite } = await supabase
    .from('user_sites')
    .select('role')
    .eq('user_id', user.id)
    .eq('site_id', siteId)
    .single();

  if (!userSite) {
    return NextResponse.json({
      error: '해당 사이트에 대한 권한이 없습니다.',
    }, { status: 403 });
  }

  // publish.yml 생성
  const workflowContent = generatePublishWorkflow({
    siteId,
    scheduleTimes: scheduleTimes.slice(0, dailyCount || scheduleTimes.length),
    count: '1',
  });

  const [owner, repo] = GITHUB_REPO.split('/');
  const apiBase = `https://api.github.com/repos/${owner}/${repo}`;
  const headers = {
    'Authorization': `Bearer ${GITHUB_TOKEN}`,
    'Accept': 'application/vnd.github.v3+json',
    'Content-Type': 'application/json',
  };

  try {
    // 기존 파일 sha 조회 (업데이트 시 필요)
    let existingSha = null;
    const getResp = await fetch(`${apiBase}/contents/${WORKFLOW_PATH}`, { headers });
    if (getResp.ok) {
      const existing = await getResp.json();
      existingSha = existing.sha;
    }

    // 파일 생성/업데이트
    const putResp = await fetch(`${apiBase}/contents/${WORKFLOW_PATH}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({
        message: `chore: update publish schedule [${scheduleTimes.join(', ')}]`,
        content: Buffer.from(workflowContent).toString('base64'),
        ...(existingSha ? { sha: existingSha } : {}),
      }),
    });

    if (putResp.ok) {
      return NextResponse.json({
        success: true,
        message: `스케줄이 GitHub에 반영되었습니다 (${scheduleTimes.join(', ')})`,
        repo: GITHUB_REPO,
        crons: scheduleTimes.length,
      });
    }

    const errorBody = await putResp.text();
    return NextResponse.json({
      error: `GitHub API 실패: ${putResp.status}`,
      detail: errorBody,
      guide: putResp.status === 404
        ? 'GITHUB_REPO를 확인하세요. fork한 repo 주소가 맞는지 확인해주세요.'
        : putResp.status === 403
        ? 'GITHUB_TOKEN 권한을 확인하세요 (repo + workflow 스코프 필요).'
        : null,
    }, { status: putResp.status });
  } catch (err) {
    return NextResponse.json({
      error: '네트워크 오류',
      detail: err.message,
    }, { status: 500 });
  }
}
