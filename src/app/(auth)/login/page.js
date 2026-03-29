'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { signIn, signUp } from '@/lib/supabase';
import { Card, InputField, ActionButton } from '@/components/ui';

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [signupSuccess, setSignupSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'login') {
        await signIn(email, password);
        router.push('/dashboard');
      } else {
        if (password !== passwordConfirm) {
          setError('\ube44\ubc00\ubc88\ud638\uac00 \uc77c\uce58\ud558\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4');
          setLoading(false);
          return;
        }
        await signUp(email, password, displayName);
        setSignupSuccess(true);
      }
    } catch (err) {
      const msg = err.message || '오류가 발생했습니다';
      const messages = {
        'Invalid login credentials': '\uc774\uba54\uc77c \ub610\ub294 \ube44\ubc00\ubc88\ud638\uac00 \uc62c\ubc14\ub974\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4',
        'Email not confirmed': '\uc774\uba54\uc77c \uc778\uc99d\uc774 \uc644\ub8cc\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4. \uba54\uc77c\ud568\uc744 \ud655\uc778\ud574\uc8fc\uc138\uc694.',
        'User already registered': '\uc774\ubbf8 \uac00\uc785\ub41c \uc774\uba54\uc77c\uc785\ub2c8\ub2e4',
        'Password should be at least 6 characters': '\ube44\ubc00\ubc88\ud638\ub294 6\uc790 \uc774\uc0c1\uc774\uc5b4\uc57c \ud569\ub2c8\ub2e4',
        'Signups not allowed for this instance': '\ud68c\uc6d0\uac00\uc785\uc774 \ube44\ud65c\uc131\ud654\ub418\uc5b4 \uc788\uc2b5\ub2c8\ub2e4',
      };
      setError(messages[msg] || msg);
    } finally {
      setLoading(false);
    }
  };

  if (signupSuccess) {
    return (
      <div style={styles.container}>
        <Card style={styles.card}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>&#x2709;&#xfe0f;</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>이메일을 확인해주세요</h2>
            <p style={{ color: 'var(--text-dim)', fontSize: 14, lineHeight: 1.6 }}>
              <strong>{email}</strong>으로 인증 메일을 보냈습니다.<br />
              메일의 링크를 클릭하면 가입이 완료됩니다.
            </p>
            <ActionButton onClick={() => { setMode('login'); setSignupSuccess(false); }} variant="secondary" style={{ marginTop: 24 }}>
              로그인으로 돌아가기
            </ActionButton>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--accent)', letterSpacing: -1 }}>AutoBlog</div>
        <div style={{ fontSize: 14, color: 'var(--text-dim)', marginTop: 4 }}>AI 기반 자동 블로그 수익화 플랫폼</div>
      </div>

      <Card style={styles.card}>
        <div style={styles.tabs}>
          <button
            onClick={() => { setMode('login'); setError(''); }}
            style={{ ...styles.tab, ...(mode === 'login' ? styles.tabActive : {}) }}
          >로그인</button>
          <button
            onClick={() => { setMode('signup'); setError(''); }}
            style={{ ...styles.tab, ...(mode === 'signup' ? styles.tabActive : {}) }}
          >회원가입</button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {mode === 'signup' && (
            <div>
              <label style={styles.label}>이름</label>
              <InputField value={displayName} onChange={setDisplayName} placeholder="표시될 이름" />
            </div>
          )}
          <div>
            <label style={styles.label}>이메일</label>
            <InputField value={email} onChange={setEmail} placeholder="email@example.com" type="email" />
          </div>
          <div>
            <label style={styles.label}>비밀번호</label>
            <div style={{ position: 'relative' }}>
              <InputField value={password} onChange={setPassword} placeholder={mode === 'signup' ? '6자 이상' : '\ube44\ubc00\ubc88\ud638'} type={showPassword ? 'text' : 'password'} />
              <button type="button" onClick={() => setShowPassword(!showPassword)} style={{
                position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                border: 'none', background: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--text-dim)',
              }}>{showPassword ? '\uc228\uae30\uae30' : '\ubcf4\uae30'}</button>
            </div>
          </div>
          {mode === 'signup' && (
            <div>
              <label style={styles.label}>비밀번호 확인</label>
              <InputField value={passwordConfirm} onChange={setPasswordConfirm} placeholder="\ube44\ubc00\ubc88\ud638 \ub2e4\uc2dc \uc785\ub825" type={showPassword ? 'text' : 'password'} />
            </div>
          )}

          {error && (
            <div style={styles.error}>{error}</div>
          )}

          <ActionButton
            onClick={handleSubmit}
            disabled={loading || !email || !password}
            style={{ width: '100%', marginTop: 8, padding: '12px 20px' }}
          >
            {loading ? '처리 중...' : mode === 'login' ? '로그인' : '무료로 시작하기'}
          </ActionButton>
        </form>

        {mode === 'signup' && (
          <div style={{ marginTop: 16, padding: 16, background: 'var(--accent-bg)', borderRadius: 12, fontSize: 12, color: 'var(--text-secondary)' }}>
            <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--accent)' }}>&#x1f381; 7일 Premium 무료 체험</div>
            가입 즉시 Premium 기능을 7일간 무료로 체험할 수 있습니다. Golden Mode, 고급 분석, 맞춤 스케줄 등 모든 프리미엄 기능을 경험해보세요.
          </div>
        )}
      </Card>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh', display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    padding: 24, background: 'var(--bg)',
  },
  header: { textAlign: 'center', marginBottom: 32 },
  card: { width: '100%', maxWidth: 400, padding: 32 },
  tabs: {
    display: 'flex', marginBottom: 24, background: 'var(--input-bg)',
    borderRadius: 10, padding: 4,
  },
  tab: {
    flex: 1, padding: '10px 0', border: 'none', background: 'transparent',
    borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: 'pointer',
    color: 'var(--text-dim)', transition: 'all 0.2s',
  },
  tabActive: {
    background: 'var(--card)', color: 'var(--text)',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 },
  error: {
    padding: '10px 14px', borderRadius: 10, fontSize: 12,
    background: 'var(--red-bg)', color: 'var(--red)', fontWeight: 500,
  },
};
