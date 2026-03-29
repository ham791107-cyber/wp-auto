// ═══════════════════════════════════════════
// Plan Definitions & Feature Flags
// ═══════════════════════════════════════════

export const PLANS = {
  standard: {
    id: 'standard',
    name: 'Standard',
    price: { monthly: 29000, yearly: 290000 },
    maxSites: 1,
    maxDailyPosts: 4,
    maxCategories: 6,
    features: {
      goldenMode: false,
      polishing: false,
      customSchedule: false,
      modelSelection: false,
      revenueSimulation: false,
      seoAnalysis: false,
      telegramAlerts: false,
      snsAutomation: false,
      marketingContent: false,
      newsResearch: false,
      sectorResearch: false,
    },
    draftModel: 'deepseek-chat',
    polishModel: 'none',
    color: '#3b82f6',
  },
  premium: {
    id: 'premium',
    name: 'Premium',
    price: { monthly: 79000, yearly: 790000 },
    maxSites: 3,
    maxDailyPosts: 20,
    maxCategories: 999,
    features: {
      goldenMode: true,
      polishing: true,
      customSchedule: true,
      modelSelection: true,
      revenueSimulation: true,
      seoAnalysis: true,
      telegramAlerts: true,
      snsAutomation: false,
      marketingContent: false,
      newsResearch: true,
      sectorResearch: true,
    },
    draftModel: null,
    polishModel: 'claude-sonnet-4-20250514',
    color: '#7c3aed',
  },
  mama: {
    id: 'mama',
    name: 'MaMa',
    price: { monthly: 199000, yearly: 1990000 },
    maxSites: 999,
    maxDailyPosts: 999,
    maxCategories: 999,
    features: {
      goldenMode: true,
      polishing: true,
      customSchedule: true,
      modelSelection: true,
      revenueSimulation: true,
      seoAnalysis: true,
      telegramAlerts: true,
      snsAutomation: true,
      marketingContent: true,
      newsResearch: true,
      sectorResearch: true,
    },
    draftModel: null,
    polishModel: 'claude-sonnet-4-20250514',
    color: '#f59e0b',
  },
};

export const MILESTONES = [
  { id: 'first_post', label: '\uccab \uae00 \ubc1c\ud589', icon: '\ud83d\udcdd', target: 1, metric: 'total_posts' },
  { id: 'posts_10', label: '10\ud3b8 \ub2ec\uc131', icon: '\ud83d\udcda', target: 10, metric: 'total_posts' },
  { id: 'posts_30', label: '30\ud3b8 \ub2ec\uc131', icon: '\ud83c\udfc6', target: 30, metric: 'total_posts' },
  { id: 'adsense_approved', label: 'AdSense \uc2b9\uc778', icon: '\u2705', target: 1, metric: 'adsense_approved' },
  { id: 'first_revenue', label: '\uccab \uc218\uc775 \ub2ec\uc131', icon: '\ud83d\udcb0', target: 1, metric: 'first_revenue' },
  { id: 'revenue_10k', label: '\uc6d4 1\ub9cc\uc6d0 \uc218\uc775', icon: '\ud83d\udd25', target: 10000, metric: 'monthly_revenue' },
  { id: 'revenue_100k', label: '\uc6d4 10\ub9cc\uc6d0 \uc218\uc775', icon: '\ud83d\ude80', target: 100000, metric: 'monthly_revenue' },
  { id: 'revenue_500k', label: '\uc6d4 50\ub9cc\uc6d0 \uc218\uc775', icon: '\u2b50', target: 500000, metric: 'monthly_revenue' },
];

export const CONSUMER_CATEGORIES = [
  { id: 'product', label: '\ud83d\uded2 제품 리뷰/비교', items: [
    { slug: 'ai-tools', ko: 'AI 도구', icon: '\ud83e\udd16', plans: ['standard', 'premium', 'mama'] },
    { slug: 'tech', ko: 'IT/전자기기', icon: '\ud83d\udcbb', plans: ['standard', 'premium', 'mama'] },
    { slug: 'smart-home', ko: '스마트홈', icon: '\ud83c\udfe0', plans: ['standard', 'premium', 'mama'] },
    { slug: 'pet', ko: '반려동물', icon: '\ud83d\udc3e', plans: ['standard', 'premium', 'mama'] },
    { slug: 'health', ko: '건강/웰니스', icon: '\ud83d\udcaa', plans: ['standard', 'premium', 'mama'] },
    { slug: 'finance', ko: '재테크', icon: '\ud83d\udcb0', plans: ['standard', 'premium', 'mama'] },
    { slug: 'beauty', ko: '뷰티', icon: '\ud83d\udc84', plans: ['standard', 'premium', 'mama'] },
    { slug: 'baby', ko: '육아/유아', icon: '\ud83d\udc76', plans: ['standard', 'premium', 'mama'] },
    { slug: 'appliance', ko: '생활가전', icon: '\ud83d\udd0c', plans: ['standard', 'premium', 'mama'] },
    { slug: 'fitness', ko: '운동기구', icon: '\ud83c\udfcb\ufe0f', plans: ['standard', 'premium', 'mama'] },
    { slug: 'education', ko: '교육/생산성', icon: '\ud83d\udcda', plans: ['standard', 'premium', 'mama'] },
  ]},
  { id: 'info', label: '\ud83d\udccb 정보 서비스', items: [
    { slug: 'gov-support', ko: '정부지원/보조금', icon: '\ud83c\udfdb\ufe0f', plans: ['standard', 'premium', 'mama'] },
    { slug: 'tax-guide', ko: '세무/절세', icon: '\ud83e\uddfe', plans: ['standard', 'premium', 'mama'] },
    { slug: 'travel', ko: '여행 정보', icon: '\u2708\ufe0f', plans: ['standard', 'premium', 'mama'] },
    { slug: 'agency', ko: '기관 정보', icon: '\ud83c\udfe2', plans: ['standard', 'premium', 'mama'] },
    { slug: 'event', ko: '행사/컨퍼런스', icon: '\ud83c\udfea', plans: ['standard', 'premium', 'mama'] },
  ]},
  { id: 'promo', label: '\ud83d\udce2 홍보/마케팅', items: [
    { slug: 'niche-promo', ko: '니치 홍보용', icon: '\ud83d\udce3', plans: ['standard', 'premium', 'mama'] },
    { slug: 'brand', ko: '브랜드 콘텐츠', icon: '\ud83c\udff7\ufe0f', plans: ['standard', 'premium', 'mama'] },
    { slug: 'compare-land', ko: '비교 랜딩', icon: '\u2696\ufe0f', plans: ['standard', 'premium', 'mama'] },
  ]},
  { id: 'news', label: '\ud83d\udcf0 뉴스/리서치', items: [
    { slug: 'news-sbs', ko: 'SBS 뉴스', icon: '\ud83d\udcfa', plans: ['premium', 'mama'] },
    { slug: 'news-kbs', ko: 'KBS 뉴스', icon: '\ud83d\udcfa', plans: ['premium', 'mama'] },
    { slug: 'news-jtbc', ko: 'JTBC 뉴스', icon: '\ud83d\udcfa', plans: ['premium', 'mama'] },
    { slug: 'sns-trend', ko: 'SNS 인기 이슈', icon: '\ud83d\udd25', plans: ['premium', 'mama'] },
    { slug: 'top10-corp', ko: '10대 대기업', icon: '\ud83c\udfe2', plans: ['premium', 'mama'] },
  ]},
  { id: 'sector', label: '\ud83d\udcca 섹터 리서치', items: [
    { slug: 's-semi', ko: '반도체', icon: '\ud83d\udd2c', plans: ['premium', 'mama'] },
    { slug: 's-ai', ko: 'AI/인공지능', icon: '\ud83e\udd16', plans: ['premium', 'mama'] },
    { slug: 's-defense', ko: '방산', icon: '\ud83d\udee1\ufe0f', plans: ['premium', 'mama'] },
    { slug: 's-pharma', ko: '제약/바이오', icon: '\ud83d\udc8a', plans: ['premium', 'mama'] },
    { slug: 's-robot', ko: '로봇', icon: '\ud83e\uddbe', plans: ['premium', 'mama'] },
    { slug: 's-ev', ko: '전기차/2차전지', icon: '\ud83d\udd0b', plans: ['premium', 'mama'] },
    { slug: 's-space', ko: '우주/항공', icon: '\ud83d\ude80', plans: ['premium', 'mama'] },
  ]},
];

export function getPlan(planId) {
  return PLANS[planId] || PLANS.standard;
}

export function hasFeature(planId, feature) {
  const plan = getPlan(planId);
  return plan.features[feature] === true;
}

export function canAccessCategory(planId, categorySlug) {
  for (const group of CONSUMER_CATEGORIES) {
    const item = group.items.find(i => i.slug === categorySlug);
    if (item) {
      return item.plans.includes(planId);
    }
  }
  return false;
}

export function getAvailableCategories(planId) {
  return CONSUMER_CATEGORIES.map(group => ({
    ...group,
    items: group.items.filter(item => item.plans.includes(planId)),
  })).filter(group => group.items.length > 0);
}
