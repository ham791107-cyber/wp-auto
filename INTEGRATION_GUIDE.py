# ============================================================
# autoblog.py 에 추가할 Supabase 로깅 코드 (패치 가이드)
# ============================================================
# 기존 autoblog.py의 발행 성공/실패 지점에 아래 코드를 삽입합니다.
#
# 1. GitHub Secrets에 추가:
#    SUPABASE_URL = https://xxxxx.supabase.co
#    SUPABASE_KEY = sb_publishable_xxxxx
#
# 2. requirements.txt에 추가:
#    supabase>=2.0.0
#
# 3. autoblog.py 상단에 import 추가:
#    from report_agent import log_publish, log_cost, log_alert
#
# 4. 발행 성공 시 (WordPress 포스트 생성 후):
#
#    log_publish({
#        "title": post_title,
#        "url": post_url,
#        "keyword": keyword,
#        "intent": intent,
#        "category": category,
#        "pipeline": pipeline_name,  # 'autoblog', 'hotdeal', 'promo'
#        "hook_id": hook_id,
#        "content_length": len(content),
#        "has_image": bool(image_url),
#        "image_tier": image_tier,
#        "has_coupang": "coupang" in content.lower(),
#        "has_tenping": "tenping" in content.lower() or "리더스cpa" in content.lower(),
#        "has_email_cta": "stibee" in content.lower(),
#        "sns_shared": shared_platforms,  # ['facebook', 'pinterest']
#        "status": "published",
#    })
#
# 5. 발행 실패 시:
#
#    log_publish({
#        "title": post_title or keyword,
#        "keyword": keyword,
#        "pipeline": pipeline_name,
#        "status": "failed",
#        "error_message": str(error)[:500],
#    })
#
# 6. API 호출 시 (DeepSeek/Claude 호출 후):
#
#    log_cost({
#        "model": "deepseek-chat",
#        "provider": "deepseek",
#        "purpose": "content",  # 'content', 'title', 'polish', 'image'
#        "tokens_input": usage.get("prompt_tokens", 0),
#        "tokens_output": usage.get("completion_tokens", 0),
#        "cost_usd": calculated_cost_usd,
#        "cost_krw": int(calculated_cost_usd * 1450),
#        "pipeline": pipeline_name,
#    })
#
# 7. 에러 발생 시 알림:
#
#    log_alert(
#        title=f"발행 실패: {keyword}",
#        message=f"에러: {str(error)[:200]}",
#        alert_type="publish_fail",
#        severity="warning"  # or "critical" if 연속 실패
#    )
#
# ============================================================
# GitHub Actions 워크플로우 env 추가:
#
#   env:
#     SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
#     SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
#     SITE_ID: site-1
#
# ============================================================
