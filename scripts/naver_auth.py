#!/usr/bin/env python3
"""
네이버 OAuth 2.0 토큰 발급 도구
================================
최초 1회 실행하여 Refresh Token을 발급받고,
GitHub Secrets에 NAVER_REFRESH_TOKEN으로 저장하세요.

사용법:
  1. developers.naver.com에서 앱 등록 (카페 API 권한 추가)
  2. 환경변수 설정:
     export NAVER_CLIENT_ID=your_client_id
     export NAVER_CLIENT_SECRET=your_client_secret
  3. 실행:
     python scripts/naver_auth.py
  4. 브라우저에서 네이버 로그인 + 동의
  5. 출력된 Refresh Token을 GitHub Secrets에 저장
"""

import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8989/callback"
STATE = "autoblog_naver_auth"

if not CLIENT_ID or not CLIENT_SECRET:
    print("NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 환경변수를 설정하세요.")
    print("  export NAVER_CLIENT_ID=your_client_id")
    print("  export NAVER_CLIENT_SECRET=your_client_secret")
    sys.exit(1)


auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        auth_code = query.get("code", [None])[0]
        state = query.get("state", [None])[0]

        if auth_code and state == STATE:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("인증 완료! 이 창을 닫으세요.".encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization failed.")

    def log_message(self, format, *args):
        pass


def main():
    import webbrowser
    import requests

    # Step 1: 인증 URL 열기
    auth_url = (
        f"https://nid.naver.com/oauth2.0/authorize"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&state={STATE}"
    )

    print("=" * 50)
    print("네이버 OAuth 인증")
    print("=" * 50)
    print(f"\n브라우저에서 네이버 로그인을 진행하세요...")
    print(f"(자동으로 열리지 않으면 아래 URL을 직접 열어주세요)")
    print(f"\n{auth_url}\n")

    webbrowser.open(auth_url)

    # Step 2: 콜백 대기
    server = HTTPServer(("localhost", 8989), CallbackHandler)
    server.handle_request()

    if not auth_code:
        print("인증 코드를 받지 못했습니다.")
        sys.exit(1)

    print(f"인증 코드 수신 완료")

    # Step 3: Access Token + Refresh Token 발급
    token_resp = requests.post(
        "https://nid.naver.com/oauth2.0/token",
        params={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "state": STATE,
            "redirect_uri": REDIRECT_URI,
        }
    )

    tokens = token_resp.json()

    if "access_token" not in tokens:
        print(f"토큰 발급 실패: {json.dumps(tokens, indent=2)}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("토큰 발급 성공!")
    print("=" * 50)
    print(f"\nAccess Token:  {tokens['access_token'][:20]}...")
    print(f"Refresh Token: {tokens['refresh_token']}")
    print(f"만료:          {tokens.get('expires_in', '?')}초")
    print(f"\n아래 값을 GitHub Secrets에 저장하세요:")
    print(f"  NAVER_REFRESH_TOKEN = {tokens['refresh_token']}")
    print(f"  NAVER_CLIENT_ID     = {CLIENT_ID}")
    print(f"  NAVER_CLIENT_SECRET = {CLIENT_SECRET}")


if __name__ == "__main__":
    main()
