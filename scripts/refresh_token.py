#!/usr/bin/env python3
"""장기 토큰(60일)을 갱신해 새 토큰을 stdout 한 줄로 출력한다. 로그에는 만료일만 남긴다."""
import json, os, sys, urllib.request, urllib.parse
tok = os.environ["IG_TOKEN"]
q = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": tok})
with urllib.request.urlopen("https://graph.instagram.com/refresh_access_token?" + q, timeout=60) as r:
    d = json.loads(r.read())
print(d["access_token"])
print(f"새 토큰 유효기간 {d.get('expires_in', 0)//86400}일", file=sys.stderr)
