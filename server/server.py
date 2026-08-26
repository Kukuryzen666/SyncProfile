import collections
import datetime
import html
import json
import os
import secrets
import sqlite3
import sys
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DB_PATH = os.environ.get("SYNC_DB_PATH", "sync_profiles.db")
SERVER_PORT = int(os.environ.get("PORT", "8000"))
SERVER_HOST = os.environ.get("HOST", "0.0.0.0")
REQUIRE_AUTH_KEY = os.environ.get("SYNC_AUTH_KEY", "").strip()
COOKIE_NAME = "sync_access"
SECRET_ACCESS_COOKIE = os.environ.get(
    "SYNC_SECRET_COOKIE", "36cbbc089c4c01bfbe97b33bdf431f63324e0ad0280b7166"
).strip()
MAX_REQUESTS_PER_MINUTE = int(os.environ.get("MAX_REQUESTS_PER_MINUTE", "240"))

COLOR_NAMES = {
    0: ("Синий", "#60A5FA"),
    1: ("Зеленый", "#4ADE80"),
    2: ("Оранжевый", "#FF9500"),
    3: ("Красный", "#FB5252"),
    4: ("Фиолетовый", "#A855F7"),
    5: ("Бирюзовый", "#22D3EE"),
    6: ("Розовый", "#F472B6"),
    7: ("Синий диаг. / Серый", "#60A5FA"),
    8: ("Зеленый диаг.", "#4ADE80"),
    9: ("Оранжевый диаг.", "#FF9500"),
    10: ("Красный диаг.", "#FB5252"),
    11: ("Фиолетовый диаг.", "#A855F7"),
    12: ("Бирюзовый диаг.", "#22D3EE"),
    13: ("Розовый диаг.", "#F472B6"),
    14: ("Сине-красный с ромбом", "#60A5FA"),
    15: ("Оранжево-зеленый с ромбом", "#FF9500"),
    16: ("Зелено-красный с ромбом", "#4ADE80"),
    17: ("Бирюзово-зеленый с ромбом", "#22D3EE"),
    18: ("Морской-персиковый с ромбом", "#22D3EE"),
    19: ("Фиолетово-оранжевый с ромбом", "#A855F7"),
    20: ("Сине-оранжевый с ромбом", "#60A5FA"),
}


class RateLimiter:
    def __init__(self, max_requests: int = MAX_REQUESTS_PER_MINUTE, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._requests: Dict[str, collections.deque] = {}
        self._last_cleanup = time.time()

    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            if now - self._last_cleanup > 300:
                self._requests = {
                    k: q for k, q in self._requests.items()
                    if q and q[-1] > cutoff
                }
                self._last_cleanup = now

            if ip not in self._requests:
                self._requests[ip] = collections.deque([now])
                return True

            q = self._requests[ip]
            while q and q[0] <= cutoff:
                q.popleft()

            if len(q) >= self.max_requests:
                return False

            q.append(now)
            return True


rate_limiter = RateLimiter()


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._cache_lock = threading.Lock()
        self._conn_lock = threading.Lock()
        self._connections: List[sqlite3.Connection] = []
        self._all_profiles_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._last_updated_at: int = int(time.time())
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                conn.execute("PRAGMA temp_store = MEMORY;")
                conn.execute("PRAGMA mmap_size = 268435456;")
                conn.execute("PRAGMA cache_size = -64000;")
                conn.execute("PRAGMA busy_timeout = 5000;")
            except Exception:
                pass
            with self._conn_lock:
                self._connections.append(conn)
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA temp_store = MEMORY;")
            conn.execute("PRAGMA mmap_size = 268435456;")
            conn.execute("PRAGMA cache_size = -64000;")
            conn.execute("PRAGMA busy_timeout = 5000;")
        except Exception:
            pass

        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id INTEGER PRIMARY KEY,
                    premium INTEGER DEFAULT 1,
                    emoji_status_id INTEGER DEFAULT 0,
                    name_color INTEGER DEFAULT 0,
                    name_bg_emoji_id INTEGER DEFAULT 0,
                    profile_color INTEGER DEFAULT 0,
                    profile_bg_emoji_id INTEGER DEFAULT 0,
                    custom_badge TEXT DEFAULT '',
                    client_type TEXT DEFAULT '',
                    auth_key TEXT DEFAULT '',
                    created_at INTEGER,
                    updated_at INTEGER
                )
                """
            )
            try:
                conn.execute("ALTER TABLE profiles ADD COLUMN client_type TEXT DEFAULT ''")
            except Exception:
                pass
            conn.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON profiles(updated_at)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER,
                    created_at INTEGER,
                    last_used INTEGER
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        conn.close()

    def _invalidate_cache(self):
        with self._cache_lock:
            self._all_profiles_cache = None
            self._last_updated_at = int(time.time())

    def get_last_updated_at(self) -> int:
        return self._last_updated_at

    def create_session(self, user_id: int) -> str:
        token = secrets.token_hex(24)
        now = int(time.time())
        conn = self._get_connection()
        with conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, last_used) VALUES (?, ?, ?, ?)",
                (token, user_id, now, now),
            )
        return token

    def validate_session(self, token: str) -> Optional[int]:
        if not token or len(token) < 16:
            return None
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
        row = cursor.fetchone()
        if row:
            now = int(time.time())
            with conn:
                conn.execute("UPDATE sessions SET last_used = ? WHERE token = ?", (now, token))
            return row["user_id"]
        return None

    def cleanup_expired_sessions(self, max_age_seconds: int = 90 * 86400) -> int:
        cutoff = int(time.time()) - max_age_seconds
        conn = self._get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE last_used < ?", (cutoff,))
            return cursor.rowcount

    def upsert_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        user_id = int(data["user_id"])
        if user_id <= 0 or user_id > 9223372036854775807:
            raise ValueError(f"Invalid user_id: {user_id}")

        premium = 1 if data.get("premium", True) else 0
        emoji_status_id = max(0, int(data.get("emoji_status_id", 0) or 0))
        name_color = min(max(0, int(data.get("name_color", 0) or 0)), 20)
        name_bg_emoji_id = max(0, int(data.get("name_bg_emoji_id", 0) or 0))
        profile_color = min(max(0, int(data.get("profile_color", 0) or 0)), 20)
        profile_bg_emoji_id = max(0, int(data.get("profile_bg_emoji_id", 0) or 0))
        custom_badge = str(data.get("custom_badge", "") or "").strip()[:64]
        client_type = str(data.get("client_type", "") or "").strip()[:32]
        auth_key = str(data.get("auth_key", "") or "").strip()[:128]
        now = int(time.time())

        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                INSERT INTO profiles (
                    user_id, premium, emoji_status_id, name_color, name_bg_emoji_id,
                    profile_color, profile_bg_emoji_id, custom_badge, client_type, auth_key, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    premium = excluded.premium,
                    emoji_status_id = excluded.emoji_status_id,
                    name_color = excluded.name_color,
                    name_bg_emoji_id = excluded.name_bg_emoji_id,
                    profile_color = excluded.profile_color,
                    profile_bg_emoji_id = excluded.profile_bg_emoji_id,
                    custom_badge = excluded.custom_badge,
                    client_type = excluded.client_type,
                    auth_key = CASE WHEN excluded.auth_key != '' THEN excluded.auth_key ELSE profiles.auth_key END,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    premium,
                    emoji_status_id,
                    name_color,
                    name_bg_emoji_id,
                    profile_color,
                    profile_bg_emoji_id,
                    custom_badge,
                    client_type,
                    auth_key,
                    now,
                    now,
                ),
            )
        profile = {
            "user_id": user_id,
            "premium": bool(premium),
            "emoji_status_id": emoji_status_id,
            "name_color": name_color,
            "name_bg_emoji_id": name_bg_emoji_id,
            "profile_color": profile_color,
            "profile_bg_emoji_id": profile_bg_emoji_id,
            "custom_badge": custom_badge,
            "client_type": client_type,
            "updated_at": now,
        }
        with self._cache_lock:
            self._last_updated_at = now
            if self._all_profiles_cache is not None:
                self._all_profiles_cache[str(user_id)] = profile
        return profile

    def get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._cache_lock:
            if self._all_profiles_cache is not None:
                return self._all_profiles_cache.get(str(user_id))

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "premium": bool(row["premium"]),
            "emoji_status_id": row["emoji_status_id"],
            "name_color": row["name_color"],
            "name_bg_emoji_id": row["name_bg_emoji_id"],
            "profile_color": row["profile_color"],
            "profile_bg_emoji_id": row["profile_bg_emoji_id"],
            "custom_badge": row["custom_badge"],
            "client_type": row["client_type"] if "client_type" in row.keys() else "",
            "updated_at": row["updated_at"],
        }

    def get_profiles_batch(self, user_ids: List[int]) -> Dict[str, Dict[str, Any]]:
        if not user_ids:
            return {}
        valid_uids = [int(u) for u in set(user_ids) if isinstance(u, (int, str)) and str(u).isdigit() and int(u) > 0][:500]
        if not valid_uids:
            return {}

        with self._cache_lock:
            if self._all_profiles_cache is not None:
                return {
                    str(uid): self._all_profiles_cache[str(uid)]
                    for uid in valid_uids
                    if str(uid) in self._all_profiles_cache
                }

        placeholders = ",".join("?" for _ in valid_uids)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM profiles WHERE user_id IN ({placeholders})", valid_uids
        )
        results = {}
        for row in cursor.fetchall():
            results[str(row["user_id"])] = {
                "user_id": row["user_id"],
                "premium": bool(row["premium"]),
                "emoji_status_id": row["emoji_status_id"],
                "name_color": row["name_color"],
                "name_bg_emoji_id": row["name_bg_emoji_id"],
                "profile_color": row["profile_color"],
                "profile_bg_emoji_id": row["profile_bg_emoji_id"],
                "custom_badge": row["custom_badge"],
                "client_type": row["client_type"] if "client_type" in row.keys() else "",
                "updated_at": row["updated_at"],
            }
        return results

    def close(self):
        with self._conn_lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
        if hasattr(self._local, "conn"):
            self._local.conn = None

    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        with self._cache_lock:
            if self._all_profiles_cache is not None:
                return self._all_profiles_cache

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles ORDER BY updated_at DESC")
        results = {}
        for row in cursor.fetchall():
            results[str(row["user_id"])] = {
                "user_id": row["user_id"],
                "premium": bool(row["premium"]),
                "emoji_status_id": row["emoji_status_id"],
                "name_color": row["name_color"],
                "name_bg_emoji_id": row["name_bg_emoji_id"],
                "profile_color": row["profile_color"],
                "profile_bg_emoji_id": row["profile_bg_emoji_id"],
                "custom_badge": row["custom_badge"],
                "client_type": row["client_type"] if "client_type" in row.keys() else "",
                "updated_at": row["updated_at"],
            }

        with self._cache_lock:
            self._all_profiles_cache = results

        return results

    def get_profiles_updated_since(self, since_timestamp: int) -> Dict[str, Dict[str, Any]]:
        if since_timestamp <= 0:
            return self.get_all_profiles()

        with self._cache_lock:
            if self._all_profiles_cache is not None:
                return {
                    k: v for k, v in self._all_profiles_cache.items()
                    if v.get("updated_at", 0) > since_timestamp
                }

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM profiles WHERE updated_at > ? ORDER BY updated_at DESC",
            (since_timestamp,),
        )
        results = {}
        for row in cursor.fetchall():
            results[str(row["user_id"])] = {
                "user_id": row["user_id"],
                "premium": bool(row["premium"]),
                "emoji_status_id": row["emoji_status_id"],
                "name_color": row["name_color"],
                "name_bg_emoji_id": row["name_bg_emoji_id"],
                "profile_color": row["profile_color"],
                "profile_bg_emoji_id": row["profile_bg_emoji_id"],
                "custom_badge": row["custom_badge"],
                "client_type": row["client_type"] if "client_type" in row.keys() else "",
                "updated_at": row["updated_at"],
            }
        return results

    def get_stats(self) -> Dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM profiles")
        count = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as scount FROM sessions")
        scount = cursor.fetchone()["scount"]
        return {
            "total_profiles": count,
            "active_sessions": scount,
            "server_time": int(time.time()),
            "server_time_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }


db = Database()


class StandaloneHTTPHandler(BaseHTTPRequestHandler):
    def _get_client_ip(self) -> str:
        fwd = self.headers.get("X-Forwarded-For", "").strip()
        if fwd:
            return fwd.split(",")[0].strip()
        real_ip = self.headers.get("X-Real-IP", "").strip()
        if real_ip:
            return real_ip
        if hasattr(self, "client_address") and self.client_address:
            return str(self.client_address[0])
        return "127.0.0.1"

    def _check_rate_limit(self) -> bool:
        ip = self._get_client_ip()
        if not rate_limiter.is_allowed(ip):
            self.send_response(429)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Retry-After", "60")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"error": "Too Many Requests", "message": "Превышен лимит запросов. Пожалуйста, подождите."},
                    ensure_ascii=False,
                ).encode("utf-8")
            )
            return False
        return True

    def _parse_cookies(self) -> Dict[str, str]:
        cookie_header = self.headers.get("Cookie", "")
        cookies = {}
        if cookie_header:
            for item in cookie_header.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookies[k.strip()] = v.strip()
        return cookies

    def _get_auth_session(self) -> Optional[int]:
        cookies = self._parse_cookies()
        token = cookies.get(COOKIE_NAME) or cookies.get("sync_session")
        if token:
            if SECRET_ACCESS_COOKIE and secrets.compare_digest(token, SECRET_ACCESS_COOKIE):
                return 1
            user_id = db.validate_session(token)
            if user_id is not None:
                return user_id

        if REQUIRE_AUTH_KEY:
            client_auth = self.headers.get("X-Auth-Key", "").strip()
            if client_auth and secrets.compare_digest(client_auth, REQUIRE_AUTH_KEY):
                return 1

        return None

    def _send_json(self, status: int, data: Any, set_cookie: Optional[str] = None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Key, Cookie")
        self.send_header("Access-Control-Allow-Credentials", "true")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, html_content: str, set_cookie: Optional[str] = None):
        body = html_content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Key, Cookie")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.end_headers()

    def do_GET(self):
        if not self._check_rate_limit():
            return

        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/health":
            stats = db.get_stats()
            auth_user = self._get_auth_session()
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "SyncProfile Server",
                    "version": "1.0.0",
                    "authenticated": auth_user is not None,
                    "cookie_required": True,
                    **stats,
                },
            )
            return

        if path == "/api/profiles/all":
            if not self._get_auth_session():
                self._send_json(
                    401,
                    {
                        "error": "Unauthorized: Cookie required",
                        "message": f"Доступ запрещен. Требуется Cookie '{COOKIE_NAME}'",
                    },
                )
                return

            last_mod = db.get_last_updated_at()
            etag = f'"{last_mod}"'
            client_etag = self.headers.get("If-None-Match", "").strip()
            if client_etag and (client_etag == etag or client_etag == f'W/{etag}'):
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return

            all_profiles = db.get_all_profiles()
            body = json.dumps(
                {
                    "status": "ok",
                    "total": len(all_profiles),
                    "profiles": all_profiles,
                    "sync_time": int(time.time()),
                },
                ensure_ascii=False,
            ).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("ETag", etag)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Key, Cookie, If-None-Match")
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/profiles/updates":
            if not self._get_auth_session():
                self._send_json(
                    401,
                    {
                        "error": "Unauthorized: Cookie required",
                        "message": f"Доступ запрещен. Требуется Cookie '{COOKIE_NAME}'",
                    },
                )
                return

            qs = parse_qs(parsed.query)
            try:
                since_ts = int(qs.get("since", ["0"])[0])
            except (ValueError, TypeError):
                since_ts = 0

            last_mod = db.get_last_updated_at()
            etag = f'"{last_mod}"'
            client_etag = self.headers.get("If-None-Match", "").strip()

            if since_ts > 0 and since_ts >= last_mod:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return

            if client_etag and (client_etag == etag or client_etag == f'W/{etag}') and since_ts <= 0:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return

            updates = db.get_profiles_updated_since(since_ts)
            now_ts = int(time.time())
            body = json.dumps(
                {
                    "status": "ok",
                    "since": since_ts,
                    "total": len(updates),
                    "profiles": updates,
                    "sync_time": now_ts,
                    "server_time": now_ts,
                    "last_updated_at": last_mod,
                },
                ensure_ascii=False,
            ).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("ETag", etag)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Auth-Key, Cookie, If-None-Match")
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/backup":
            if not self._get_auth_session():
                self._send_json(
                    401,
                    {
                        "error": "Unauthorized: Cookie required",
                        "message": f"Доступ запрещен. Требуется Cookie '{COOKIE_NAME}'",
                    },
                )
                return
            all_profiles = db.get_all_profiles()
            stats = db.get_stats()
            body = json.dumps(
                {
                    "service": "SyncProfile Backup",
                    "version": "1.0.0",
                    "exported_at": int(time.time()),
                    "exported_at_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "stats": stats,
                    "profiles": all_profiles,
                },
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")

            filename = f"syncprofile_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        if path.startswith("/api/profile/"):
            auth_user = self._get_auth_session()
            if auth_user is None:
                self._send_json(
                    401,
                    {
                        "error": "Unauthorized: Cookie required",
                        "message": f"Доступ запрещен. Требуется Cookie '{COOKIE_NAME}'",
                    },
                )
                return

            user_id_str = path.replace("/api/profile/", "").strip()
            try:
                user_id = int(user_id_str)
                profile = db.get_profile(user_id)
                if profile:
                    self._send_json(200, profile)
                else:
                    self._send_json(404, {"error": "Profile not found", "user_id": user_id})
            except ValueError:
                self._send_json(400, {"error": "Invalid user_id format"})
            return

        if path == "/api/stats":
            auth_user = self._get_auth_session()
            if auth_user is None:
                self._send_json(401, {"error": "Unauthorized: Cookie required"})
                return
            self._send_json(200, db.get_stats())
            return

        if path == "" or path == "/":
            stats = db.get_stats()
            status_html = self._render_status_page(stats)
            self._send_html(200, status_html)
            return

        self._send_json(404, {"error": "Endpoint not found"})

    def _render_status_page(self, stats: Dict[str, Any]) -> str:
        total_profs = stats.get("total_profiles", 0)
        return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SyncProfile Service Status</title>
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 30, 49, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #22c55e;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
            background-image: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.12), transparent 50%);
        }}
        .status-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 36px 32px;
            max-width: 520px;
            width: 100%;
            backdrop-filter: blur(12px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            text-align: center;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(34, 197, 94, 0.12);
            color: var(--accent-green);
            border: 1px solid rgba(34, 197, 94, 0.3);
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        .pulse-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent-green);
            box-shadow: 0 0 10px var(--accent-green);
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.4; transform: scale(0.85); }}
        }}
        h1 {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
            color: #ffffff;
        }}
        p.subtitle {{
            font-size: 14px;
            color: var(--text-muted);
            margin-bottom: 28px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 28px;
            text-align: left;
        }}
        .stat-item {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px;
        }}
        .stat-label {{
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-val {{
            font-size: 16px;
            font-weight: 600;
            color: var(--text-main);
        }}
        .endpoints-box {{
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 14px;
            text-align: left;
            margin-bottom: 24px;
            font-size: 13px;
        }}
        .endpoint-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }}
        .endpoint-row:last-child {{ border-bottom: none; }}
        .method {{
            font-family: monospace;
            font-size: 11px;
            font-weight: bold;
            color: var(--accent-blue);
            background: rgba(56, 189, 248, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            margin-right: 8px;
        }}
        .ep-path {{ font-family: monospace; color: var(--text-muted); }}
        .footer-note {{
            font-size: 12px;
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="status-card">
        <div class="status-badge">
            <span class="pulse-dot"></span> Все системы работают штатно
        </div>
        <h1>SyncProfile Server</h1>
        <p class="subtitle">Служба синхронизации профилей для AyuGram и exteraGram</p>

        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-label">Состояние</div>
                <div class="stat-val" style="color: var(--accent-green);">ONLINE (200 OK)</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Версия узла</div>
                <div class="stat-val">v10.1.5</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Профилей в базе</div>
                <div class="stat-val">{total_profs}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Режим хранилища</div>
                <div class="stat-val">SQLite WAL</div>
            </div>
        </div>

        <div class="endpoints-box">
            <div class="endpoint-row">
                <span><span class="method">GET</span><span class="ep-path">/health</span></span>
                <span style="color: var(--accent-green); font-size: 12px;">Active</span>
            </div>
            <div class="endpoint-row">
                <span><span class="method">GET</span><span class="ep-path">/api/profiles/updates</span></span>
                <span style="color: var(--accent-green); font-size: 12px;">Active</span>
            </div>
            <div class="endpoint-row">
                <span><span class="method">POST</span><span class="ep-path">/api/profile</span></span>
                <span style="color: var(--accent-green); font-size: 12px;">Active</span>
            </div>
        </div>

        <div class="footer-note">
            SyncProfile Node • sync.efn.mom
        </div>
    </div>
</body>
</html>"""

    def do_POST(self):
        if not self._check_rate_limit():
            return

        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0 or content_length > 1048576:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return

        try:
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
        except Exception as e:
            self._send_json(400, {"error": f"Invalid JSON payload: {e}"})
            return

        if path == "/api/auth":
            if not isinstance(data, dict) or "user_id" not in data:
                self._send_json(400, {"error": "Missing required field 'user_id'"})
                return

            try:
                user_id = int(data["user_id"])
                if user_id <= 0 or user_id > 9223372036854775807:
                    self._send_json(400, {"error": "Invalid user_id"})
                    return
            except (ValueError, TypeError):
                self._send_json(400, {"error": "user_id must be a valid integer"})
                return

            if REQUIRE_AUTH_KEY:
                client_key = str(data.get("auth_key") or self.headers.get("X-Auth-Key", "")).strip()
                if not secrets.compare_digest(client_key, REQUIRE_AUTH_KEY):
                    self._send_json(401, {"error": "Invalid auth_key"})
                    return

            try:
                session_token = db.create_session(user_id)
                cookie_header = f"{COOKIE_NAME}={session_token}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly"
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "message": "Authenticated successfully",
                        "user_id": user_id,
                        "session_token": session_token,
                    },
                    set_cookie=cookie_header,
                )
            except Exception as e:
                self._send_json(500, {"error": f"Auth error: {e}"})
            return

        if path == "/api/profile":
            if not isinstance(data, dict) or "user_id" not in data:
                self._send_json(400, {"error": "Missing required field 'user_id'"})
                return

            try:
                user_id = int(data["user_id"])
                if user_id <= 0 or user_id > 9223372036854775807:
                    self._send_json(400, {"error": "Invalid user_id"})
                    return
            except (ValueError, TypeError):
                self._send_json(400, {"error": "user_id must be a valid integer"})
                return

            auth_user = self._get_auth_session()
            session_cookie = None

            if auth_user is not None and auth_user != 1:
                if auth_user != user_id:
                    self._send_json(403, {"error": "Forbidden: You can only update your own profile"})
                    return
            elif auth_user is None:
                if REQUIRE_AUTH_KEY:
                    client_key = str(data.get("auth_key") or self.headers.get("X-Auth-Key", "")).strip()
                    if not secrets.compare_digest(client_key, REQUIRE_AUTH_KEY):
                        self._send_json(401, {"error": "Unauthorized: Cookie required or invalid auth_key"})
                        return

                token = db.create_session(user_id)
                session_cookie = f"{COOKIE_NAME}={token}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly"

            try:
                saved = db.upsert_profile(data)
                self._send_json(200, {"status": "ok", "profile": saved}, set_cookie=session_cookie)
            except Exception as e:
                self._send_json(500, {"error": f"Database error: {e}"})
            return

        if path == "/api/profiles/batch":
            auth_user = self._get_auth_session()
            if auth_user is None:
                self._send_json(
                    401,
                    {
                        "error": "Unauthorized: Cookie required",
                        "message": f"Доступ к пакетным запросам разрешен только с Cookie '{COOKIE_NAME}'",
                    },
                )
                return

            if not isinstance(data, dict) or "user_ids" not in data:
                self._send_json(400, {"error": "Missing required field 'user_ids' (list)"})
                return
            user_ids = data.get("user_ids", [])
            if not isinstance(user_ids, list):
                self._send_json(400, {"error": "'user_ids' must be a list of integers"})
                return
            try:
                profiles = db.get_profiles_batch(user_ids)
                self._send_json(200, {"profiles": profiles})
            except Exception as e:
                self._send_json(500, {"error": f"Database error: {e}"})
            return

        self._send_json(404, {"error": "Endpoint not found"})

    def log_message(self, format, *args):
        sys.stderr.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]} {args[2]}\n")


def run_standalone_server():
    server_address = (SERVER_HOST, SERVER_PORT)
    httpd = ThreadingHTTPServer(server_address, StandaloneHTTPHandler)
    print(f"SyncProfile Server running on http://{SERVER_HOST}:{SERVER_PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    run_standalone_server()
