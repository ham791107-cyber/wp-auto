import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_REPO = process.env.GITHUB_REPO || 'planxs-ai/wp-auto';

// Each workflow and its allowed input keys (GitHub 422s on unknown inputs)
const WORKFLOW_CONFIG = {
  'setup-menu': {
    file: 'setup-menu.yml',
    inputs: ['wp_url', 'wp_username', 'wp_app_password', 'site_id'],
  },
  'setup-pages': {
    file: 'setup-pages.yml',
    inputs: ['wp_url', 'wp_username', 'wp_app_password', 'site_id', 'blog_owner', 'blog_desc', 'contact_email'],
  },
  'inject-css': {
    file: 'inject-css.yml',
    inputs: ['wp_url', 'wp_username', 'wp_app_password', 'wp_login_password', 'site_id'],
  },
  'inject-css-posts': {
    file: 'inject-css-posts.yml',
    inputs: ['wp_url', 'wp_username', 'wp_app_password', 'dry_run', 'force_update'],
  },
  'publish': {
    file: 'publish.yml',
    inputs: ['wp_url', 'wp_username', 'wp_app_password', 'site_id', 'count', 'dry_run', 'pipeline', 'niche'],
  },
};

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

async function getSiteCredentials(siteId) {
  if (!siteId) return null;
  const supabase = getSupabaseAdmin();
  const { data } = await supabase
    .from('sites')
    .select('wp_url, domain, config')
    .eq('id', siteId)
    .single();
  if (!data) return null;
  return {
    wp_url: data.wp_url,
    domain: data.domain,
    wp_username: data.config?.wp_username || '',
    wp_app_password: data.config?.wp_app_password || '',
    wp_login_password: data.config?.wp_login_password || data.config?.wp_app_password || '',
  };
}

export async function POST(request) {
  if (!GITHUB_TOKEN) {
    return NextResponse.json({ error: 'GITHUB_TOKEN not configured' }, { status: 500 });
  }

  const user = await verifyAuth(request);
  if (!user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { action, siteId, inputs } = await request.json();

  const config = WORKFLOW_CONFIG[action];
  if (!config) {
    return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
  }

  // Fetch site credentials from Supabase
  const creds = await getSiteCredentials(siteId);
  if (!creds || !creds.wp_url) {
    return NextResponse.json({
      error: '사이트 인증정보를 찾을 수 없습니다. 설정에서 사이트를 먼저 연결해주세요.',
      siteId,
    }, { status: 400 });
  }

  // Build all possible values, then filter to only allowed inputs
  const allValues = {
    ...(inputs || {}),
    wp_url: creds.wp_url,
    wp_username: creds.wp_username,
    wp_app_password: creds.wp_app_password,
    wp_login_password: creds.wp_login_password,
    site_id: siteId || '',
  };

  // Only include keys that the target workflow defines (prevents GitHub 422)
  const workflowInputs = {};
  for (const key of config.inputs) {
    if (allValues[key] !== undefined && allValues[key] !== '') {
      workflowInputs[key] = String(allValues[key]);
    }
  }

  const [owner, repo] = GITHUB_REPO.split('/');

  const resp = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${config.file}/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ref: 'main', inputs: workflowInputs }),
    }
  );

  if (resp.status === 204) {
    return NextResponse.json({
      success: true, action,
      message: `${action} triggered for ${creds.domain}`,
    });
  }

  const errorBody = await resp.text();
  return NextResponse.json({
    error: `GitHub API failed: ${resp.status}`,
    detail: errorBody,
    debug: { repo: GITHUB_REPO, workflow: config.file, site: creds.domain, tokenSet: !!GITHUB_TOKEN },
  }, { status: resp.status });
}
