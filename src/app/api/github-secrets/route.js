import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_REPO = process.env.GITHUB_REPO || 'planxs-ai/wp-auto';

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
 * GitHub Secrets API: sealed box 암호화 (tweetnacl)
 */
async function encryptSecret(publicKey, secretValue) {
  const nacl = (await import('tweetnacl')).default;
  const naclUtil = (await import('tweetnacl-util')).default;

  const keyBytes = naclUtil.decodeBase64(publicKey);
  const messageBytes = naclUtil.decodeUTF8(secretValue);
  const encrypted = nacl.sealedbox
    ? nacl.sealedbox(messageBytes, keyBytes)
    : (() => {
        // tweetnacl doesn't have sealedbox — use libsodium-compatible sealed box
        // sealed box = ephemeral x25519 keypair + box
        const ephemeralKP = nacl.box.keyPair();
        const nonce = nacl.hash(
          new Uint8Array([...ephemeralKP.publicKey, ...keyBytes])
        ).slice(0, nacl.box.nonceLength);
        const ciphertext = nacl.box(messageBytes, nonce, keyBytes, ephemeralKP.secretKey);
        return new Uint8Array([...ephemeralKP.publicKey, ...ciphertext]);
      })();

  return naclUtil.encodeBase64(encrypted);
}

/**
 * GitHub repo의 public key 조회
 */
async function getRepoPublicKey() {
  const [owner, repo] = GITHUB_REPO.split('/');
  const resp = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/secrets/public-key`,
    {
      headers: {
        'Authorization': `Bearer ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
      },
    }
  );
  if (!resp.ok) {
    throw new Error(`GitHub public key 조회 실패: ${resp.status}`);
  }
  return resp.json();
}

/**
 * GitHub repo에 secret 설정
 */
async function setRepoSecret(secretName, encryptedValue, keyId) {
  const [owner, repo] = GITHUB_REPO.split('/');
  const resp = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/secrets/${secretName}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        encrypted_value: encryptedValue,
        key_id: keyId,
      }),
    }
  );
  return resp.ok || resp.status === 204;
}

/**
 * POST /api/github-secrets
 *
 * Body: {
 *   action: 'setup',          // 'setup' | 'sync-allowed-sites'
 *   siteId: 'site-xxx',       // 소유권 확인용
 *   secrets: {                 // action=setup 시
 *     DEEPSEEK_API_KEY: '...',
 *     GROK_API_KEY: '...',
 *     ...
 *   }
 * }
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

  const body = await request.json();
  const { action = 'setup', siteId, secrets = {} } = body;

  // 사이트 소유권 확인
  if (siteId) {
    const supabase = getSupabaseAdmin();
    const { data: userSite } = await supabase
      .from('user_sites')
      .select('role')
      .eq('user_id', user.id)
      .eq('site_id', siteId)
      .single();

    if (!userSite) {
      return NextResponse.json({ error: '해당 사이트에 대한 권한이 없습니다.' }, { status: 403 });
    }
  }

  try {
    const { key: publicKey, key_id: keyId } = await getRepoPublicKey();
    const results = {};

    if (action === 'setup') {
      // 사용자 입력 secrets 등록
      for (const [name, value] of Object.entries(secrets)) {
        if (!value) continue;
        const encrypted = await encryptSecret(publicKey, value);
        const ok = await setRepoSecret(name, encrypted, keyId);
        results[name] = ok ? 'success' : 'failed';
      }

      // 중앙 Supabase 정보 자동 등록
      const autoSecrets = {
        SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
        SUPABASE_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
      };
      for (const [name, value] of Object.entries(autoSecrets)) {
        if (!value) continue;
        const encrypted = await encryptSecret(publicKey, value);
        const ok = await setRepoSecret(name, encrypted, keyId);
        results[name] = ok ? 'auto' : 'failed';
      }

      // ALLOWED_SITE_IDS 자동 등록
      if (siteId) {
        const supabase = getSupabaseAdmin();
        const { data: userSites } = await supabase
          .from('user_sites')
          .select('site_id')
          .eq('user_id', user.id);

        const allowedIds = (userSites || []).map(s => s.site_id).join(',');
        const encrypted = await encryptSecret(publicKey, allowedIds);
        const ok = await setRepoSecret('ALLOWED_SITE_IDS', encrypted, keyId);
        results['ALLOWED_SITE_IDS'] = ok ? 'auto' : 'failed';
      }
    } else if (action === 'sync-allowed-sites') {
      // ALLOWED_SITE_IDS만 갱신
      const supabase = getSupabaseAdmin();
      const { data: userSites } = await supabase
        .from('user_sites')
        .select('site_id')
        .eq('user_id', user.id);

      const allowedIds = (userSites || []).map(s => s.site_id).join(',');
      const encrypted = await encryptSecret(publicKey, allowedIds);
      const ok = await setRepoSecret('ALLOWED_SITE_IDS', encrypted, keyId);
      results['ALLOWED_SITE_IDS'] = ok ? 'success' : 'failed';
    }

    const failCount = Object.values(results).filter(v => v === 'failed').length;

    return NextResponse.json({
      success: failCount === 0,
      results,
      repo: GITHUB_REPO,
      message: failCount === 0
        ? `${Object.keys(results).length}개 시크릿이 GitHub에 등록되었습니다.`
        : `${failCount}개 시크릿 등록 실패. GITHUB_TOKEN 권한을 확인하세요.`,
    });
  } catch (err) {
    return NextResponse.json({
      error: err.message,
      guide: 'GITHUB_TOKEN 권한(repo + workflow 스코프)을 확인하세요.',
    }, { status: 500 });
  }
}
