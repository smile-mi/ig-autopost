#!/usr/bin/env python3
"""posts/<YYYYMMDD>/ 폴더의 JPG 카드 + caption.txt 를 인스타 캐러셀로 게시한다.
표준 라이브러리만 사용. 이미 게시한 폴더(published.json 존재)는 건너뛴다(중복 방지).
환경변수: IG_TOKEN, IG_USER_ID, REPO(owner/name), BRANCH(기본 main),
          [선택] IG_API_BASE(테스트용), MAX_ITEMS(기본 10), DRY_RUN=1
"""
import json, os, sys, time, glob, urllib.request, urllib.parse, urllib.error

API = os.environ.get("IG_API_BASE", "https://graph.instagram.com/v21.0").rstrip("/")
TOKEN = os.environ.get("IG_TOKEN", "")
UID = os.environ.get("IG_USER_ID", "")
REPO = os.environ.get("REPO", "")
BRANCH = os.environ.get("BRANCH", "main")
RAW_BASE = os.environ.get("RAW_BASE", f"https://raw.githubusercontent.com/{REPO}/{BRANCH}").rstrip("/")
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "10"))
DRY = os.environ.get("DRY_RUN") == "1"

def call(method, path, params):
    params = dict(params, access_token=TOKEN)
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    req = urllib.request.Request(url, data=data if method == "POST" else None, method=method)
    if method == "GET":
        req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params))
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        # 토큰이 로그에 찍히지 않게 URL은 출력하지 않는다
        raise SystemExit(f"API 오류 {e.code} ({method} {path}): {body[:500]}")

def wait_finished(cid, tries=30):
    for _ in range(tries):
        st = call("GET", cid, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED": return
        if st in ("ERROR", "EXPIRED"): raise SystemExit(f"컨테이너 {cid} 상태 {st}")
        time.sleep(2 if os.environ.get("IG_API_BASE") else 5)
    raise SystemExit(f"컨테이너 {cid} 처리 시간 초과")

def publish_folder(folder):
    marker = os.path.join(folder, "published.json")
    if os.path.exists(marker):
        print(f"skip {folder}: 이미 게시됨"); return False
    imgs = sorted(glob.glob(os.path.join(folder, "*.jpg")))
    cap_path = os.path.join(folder, "caption.txt")
    if len(imgs) < 2: raise SystemExit(f"{folder}: JPG가 2장 미만")
    if not os.path.exists(cap_path): raise SystemExit(f"{folder}: caption.txt 없음")
    if len(imgs) > MAX_ITEMS: raise SystemExit(f"{folder}: {len(imgs)}장 > 상한 {MAX_ITEMS}장")
    caption = open(cap_path, encoding="utf-8").read().strip()
    date = os.path.basename(folder.rstrip("/"))
    urls = [f"{RAW_BASE}/posts/{date}/{urllib.parse.quote(os.path.basename(p))}" for p in imgs]
    print(f"{date}: {len(imgs)}장 게시 준비")
    if DRY:
        print("DRY_RUN 캡션:\n" + caption); [print(u) for u in urls]; return False
    kids = []
    for u in urls:
        r = call("POST", f"{UID}/media", {"image_url": u, "is_carousel_item": "true"})
        kids.append(r["id"])
    for k in kids: wait_finished(k)
    car = call("POST", f"{UID}/media", {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": caption})["id"]
    wait_finished(car)
    media = call("POST", f"{UID}/media_publish", {"creation_id": car})["id"]
    json.dump({"media_id": media, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "items": len(imgs)},
              open(marker, "w"), ensure_ascii=False)
    print(f"게시 완료 media_id={media}")
    return True

if __name__ == "__main__":
    if not DRY and not (TOKEN and UID and (REPO or os.environ.get("RAW_BASE"))):
        sys.exit("IG_TOKEN / IG_USER_ID / REPO 가 필요해요")
    folders = [a for a in sys.argv[1:]] or sorted(d for d in glob.glob("posts/*") if os.path.isdir(d))
    changed = [publish_folder(f) for f in folders]
    sys.exit(0)
