import os
from app.config import get_settings
import httpx

s = get_settings()
sid = (s.instagram_session_id or "").strip()
csrf = (s.instagram_csrf_token or "").strip()
print("session_id_len", len(sid))
print("csrf_len", len(csrf))
if not sid:
    print("ERROR: no session id in env")
    raise SystemExit(1)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.instagram.com/qrissummerrun/",
}
cookies = {"sessionid": sid}
if csrf:
    headers["X-CSRFToken"] = csrf
    cookies["csrftoken"] = csrf

with httpx.Client(timeout=30, headers=headers, cookies=cookies) as c:
    r = c.get("https://www.instagram.com/api/v1/users/web_profile_info/", params={"username": "qrissummerrun"})
    print("profile_status", r.status_code)
    print("profile_body_preview", r.text[:500])
    if r.status_code == 200:
        user = r.json().get("data", {}).get("user", {})
        edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
        print("media_count", len(edges))
        if edges:
            mid = edges[0]["node"]["id"]
            cr = c.get(f"https://www.instagram.com/api/v1/media/{mid}/comments/", params={"can_support_threading": "true"})
            print("comments_status", cr.status_code)
            print("comments_count", len(cr.json().get("comments", [])))
