#!/usr/bin/env python3
"""
report_agent.py — GitHub Actions에서 발행 후 Supabase에 로그 기록
사용: python report_agent.py --log-publish '{"title":"...", "keyword":"...", ...}'
      python report_agent.py --log-cost '{"model":"deepseek-chat", "cost_krw":15, ...}'
"""

import os, json, sys, argparse
from datetime import datetime

try:
    from supabase import create_client
except ImportError:
    print("pip install supabase 필요")
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SITE_ID = os.environ.get("SITE_ID", "site-1")

def get_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ SUPABASE_URL, SUPABASE_KEY 환경변수 필요")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def log_publish(data):
    """발행 로그 기록"""
    sb = get_client()
    record = {
        "site_id": SITE_ID,
        "title": data.get("title", ""),
        "url": data.get("url", ""),
        "keyword": data.get("keyword", ""),
        "intent": data.get("intent", ""),
        "category": data.get("category", ""),
        "pipeline": data.get("pipeline", "autoblog"),
        "hook_id": data.get("hook_id", ""),
        "content_length": data.get("content_length", 0),
        "has_image": data.get("has_image", False),
        "image_tier": data.get("image_tier", ""),
        "has_coupang": data.get("has_coupang", False),
        "has_tenping": data.get("has_tenping", False),
        "has_email_cta": data.get("has_email_cta", False),
        "sns_shared": data.get("sns_shared", []),
        "status": data.get("status", "published"),
        "error_message": data.get("error_message", ""),
        "published_at": data.get("published_at", datetime.now().isoformat()),
    }
    res = sb.table("publish_logs").insert(record).execute()
    print(f"✅ 발행 로그 기록: {record['title'][:40]}")
    return res

def log_cost(data):
    """API 비용 기록"""
    sb = get_client()
    record = {
        "site_id": SITE_ID,
        "model": data.get("model", "unknown"),
        "provider": data.get("provider", ""),
        "purpose": data.get("purpose", "content"),
        "tokens_input": data.get("tokens_input", 0),
        "tokens_output": data.get("tokens_output", 0),
        "cost_usd": data.get("cost_usd", 0),
        "cost_krw": data.get("cost_krw", 0),
        "pipeline": data.get("pipeline", "autoblog"),
    }
    res = sb.table("api_costs").insert(record).execute()
    print(f"✅ 비용 기록: {record['model']} ₩{record['cost_krw']}")
    return res

def log_alert(title, message, alert_type="info", severity="info"):
    """알림 생성"""
    sb = get_client()
    record = {
        "site_id": SITE_ID,
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
    }
    res = sb.table("alerts").insert(record).execute()
    print(f"✅ 알림 생성: [{severity}] {title}")
    return res

def main():
    parser = argparse.ArgumentParser(description="Supabase Report Agent")
    parser.add_argument("--log-publish", help="발행 로그 JSON")
    parser.add_argument("--log-cost", help="비용 로그 JSON")
    parser.add_argument("--alert", help="알림 생성 (JSON: title, message, type, severity)")
    args = parser.parse_args()

    if args.log_publish:
        log_publish(json.loads(args.log_publish))
    elif args.log_cost:
        log_cost(json.loads(args.log_cost))
    elif args.alert:
        d = json.loads(args.alert)
        log_alert(d["title"], d.get("message", ""), d.get("type", "info"), d.get("severity", "info"))
    else:
        print("사용법:")
        print('  python report_agent.py --log-publish \'{"title":"...", "keyword":"..."}\'')
        print('  python report_agent.py --log-cost \'{"model":"deepseek-chat", "cost_krw":15}\'')
        print('  python report_agent.py --alert \'{"title":"테스트", "message":"알림 테스트"}\'')

if __name__ == "__main__":
    main()
