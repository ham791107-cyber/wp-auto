// ═══════════════════════════════════════════
// 고객용 publish.yml 생성 유틸리티
// 대시보드 스케줄 설정 → GitHub workflow 자동 생성
// ═══════════════════════════════════════════

/**
 * KST 시간 문자열 → UTC cron 표현식 변환
 * @param {string} kstTime - 'HH:MM' 형식 (예: '08:00')
 * @returns {string} cron 표현식 (예: '0 23 * * *')
 */
export function kstToCron(kstTime) {
  const [h, m] = kstTime.split(':').map(Number);
  const utcH = (h - 9 + 24) % 24;
  return `${m} ${utcH} * * *`;
}

/**
 * 고객용 publish.yml 전체 내용 생성
 * @param {Object} params
 * @param {string} params.siteId - 사이트 ID (예: 'site-1775110395399')
 * @param {string[]} params.scheduleTimes - KST 시간 배열 (예: ['08:00', '18:00'])
 * @param {string} [params.count='1'] - 발행 편수
 * @returns {string} publish.yml 전체 내용
 */
export function generatePublishWorkflow({ siteId, scheduleTimes, count = '1' }) {
  const cronEntries = scheduleTimes
    .map(t => `    - cron: '${kstToCron(t)}'    # KST ${t}`)
    .join('\n');

  return `name: AutoBlog Publish

on:
  schedule:
${cronEntries}
  workflow_dispatch:
    inputs:
      count:
        description: '발행 편수'
        required: false
        default: '${count}'
      dry_run:
        description: '드라이런'
        type: choice
        required: false
        default: 'false'
        options:
          - 'false'
          - 'true'
      pipeline:
        description: '파이프라인'
        type: choice
        required: false
        default: 'autoblog'
        options:
          - autoblog
          - hotdeal
          - promo
      niche:
        description: '니치 필터 (빈값=전체)'
        required: false
        default: ''

permissions:
  contents: write

jobs:
  publish:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    env:
      GROK_API_KEY: \${{ secrets.GROK_API_KEY }}
      GEMINI_API_KEY: \${{ secrets.GEMINI_API_KEY }}
      CLAUDE_API_KEY: \${{ secrets.CLAUDE_API_KEY }}
      DEEPSEEK_API_KEY: \${{ secrets.DEEPSEEK_API_KEY }}
      PEXELS_API_KEY: \${{ secrets.PEXELS_API_KEY }}
      PIXABAY_API_KEY: \${{ secrets.PIXABAY_API_KEY }}
      UNSPLASH_ACCESS_KEY: \${{ secrets.UNSPLASH_ACCESS_KEY }}
      SUPABASE_URL: \${{ secrets.SUPABASE_URL }}
      SUPABASE_KEY: \${{ secrets.SUPABASE_KEY }}
      TELEGRAM_BOT_TOKEN: \${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: \${{ secrets.TELEGRAM_CHAT_ID }}
      DISCORD_WEBHOOK_URL: \${{ secrets.DISCORD_WEBHOOK_URL }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          token: \${{ secrets.GITHUB_TOKEN }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Publish
        run: |
          COUNT="\${{ github.event.inputs.count || '${count}' }}"
          DRY_RUN="\${{ github.event.inputs.dry_run || 'false' }}"
          PIPELINE="\${{ github.event.inputs.pipeline || 'autoblog' }}"
          NICHE="\${{ github.event.inputs.niche || '' }}"

          ARGS="--site-id ${siteId} --count $COUNT --pipeline $PIPELINE --golden"

          if [ "$DRY_RUN" = "true" ]; then
            ARGS="$ARGS --dry-run"
          fi
          if [ -n "$NICHE" ]; then
            ARGS="$ARGS --niche \\"$NICHE\\""
          fi

          echo "▶ python scripts/main.py $ARGS"
          python scripts/main.py $ARGS

      - name: Commit used keywords
        if: always()
        run: |
          git config user.email "bot@autoblog.com"
          git config user.name "AutoBlog Bot"
          git pull --rebase || true
          git add data/used_keywords.json || true
          git diff --staged --quiet || git commit -m "chore: update used keywords $(date +%Y-%m-%d)"
          git push || true
`;
}
