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
            auth_user = self._get_auth_session()
            all_profs = db.get_all_profiles()
            dashboard_html = self._render_dashboard(stats, auth_user, all_profs)
            self._send_html(200, dashboard_html)
            return

        self._send_json(404, {"error": "Endpoint not found"})

    def _render_dashboard(self, stats: Dict[str, Any], auth_user: Optional[int], all_profs: Dict[str, Dict[str, Any]]) -> str:
        auth_badge = (
            f'<span class="status-pill green"><span class="dot"></span> Авторизован (ID: {html.escape(str(auth_user))})</span>'
            if auth_user
            else f'<span class="status-pill amber"><span class="dot pulse"></span> Защита по Cookie ({html.escape(COOKIE_NAME)})</span>'
        )

        profiles_html = ""
        if all_profs:
            for uid_str, p in sorted(all_profs.items(), key=lambda item: item[1].get("updated_at", 0), reverse=True):
                nc = int(p.get("name_color", 0) or 0)
                prc = int(p.get("profile_color", 0) or 0)
                nc_name, nc_hex = COLOR_NAMES.get(nc, (f"Цвет #{nc}", "#A855F7"))
                prc_name, prc_hex = COLOR_NAMES.get(prc, (f"Обложка #{prc}", "#38BDF8"))
                em_id = int(p.get("emoji_status_id", 0) or 0)
                em_badge = f'<span class="tag emoji">⭐ Статус {em_id}</span>' if em_id else ''
                bg_id = int(p.get("name_bg_emoji_id", 0) or 0)
                bg_badge = f'<span class="tag pattern">✨ Узор {bg_id}</span>' if bg_id else ''
                client_raw = str(p.get("client_type") or "AyuGram")
                client = html.escape(client_raw, quote=True)
                uid_clean = html.escape(str(uid_str), quote=True)
                badge_val = html.escape(str(p.get("custom_badge") or "").strip(), quote=True)
                badge_pill = f'<span class="custom-badge-tag" style="background: {nc_hex}22; color: {nc_hex}; border: 1px solid {nc_hex}66;">{badge_val}</span>' if badge_val else ''
                
                profiles_html += f"""
                <div class="profile-card" data-uid="{uid_clean}" data-client="{client.lower()}" data-badge="{1 if badge_val else 0}" data-emoji="{1 if em_id else 0}">
                    <div class="profile-header">
                        <div class="profile-id-group">
                            <div class="avatar-placeholder" style="background: linear-gradient(135deg, {nc_hex}, {prc_hex});">
                                <span>👤</span>
                            </div>
                            <div>
                                <div class="profile-id">
                                    ID: {uid_clean}
                                    <button class="copy-btn" onclick="copyText('{uid_clean}', this)" title="Копировать ID">📋</button>
                                </div>
                                <div class="profile-client">{client} • TG Premium Active</div>
                            </div>
                        </div>
                        <span class="premium-star" title="Telegram Premium">⭐</span>
                    </div>

                    <div class="profile-colors">
                        <span class="color-pill" style="border-color: {nc_hex}; color: {nc_hex};">
                            <span class="color-circle" style="background: {nc_hex};"></span> Имя: {nc_name}
                        </span>
                        <span class="color-pill" style="border-color: {prc_hex}; color: {prc_hex};">
                            <span class="color-circle" style="background: {prc_hex};"></span> Обложка: {prc_name}
                        </span>
                    </div>

                    <div class="profile-tags">
                        {badge_pill}
                        {em_badge}
                        {bg_badge}
                    </div>

                    <div class="tg-sim-wrapper">
                        <div class="tg-sim-label">👁️ Telegram Live Preview:</div>
                        <div class="tg-sim-bubble" style="border-left: 3px solid {nc_hex};">
                            <div class="tg-sim-author-row">
                                <span class="tg-sim-author" style="color: {nc_hex};">User {uid_clean}</span>
                                {f'<span class="tg-sim-badge" style="color: {nc_hex}; border-color: {nc_hex}88;">[{badge_val}]</span>' if badge_val else ''}
                                <span class="tg-sim-star">⭐</span>
                            </div>
                            <div class="tg-sim-reply" style="border-left: 2px solid {nc_hex};">
                                <div class="tg-sim-reply-name" style="color: {nc_hex};">SyncProfile Node</div>
                                <div class="tg-sim-reply-text">Кастомный цвет и паттерны активны ✨</div>
                            </div>
                            <div class="tg-sim-text">
                                Сообщение синхронизировано
                                {f'<span class="tg-sim-em-tag">⭐ {em_id}</span>' if em_id else ''}
                            </div>
                            <div class="tg-sim-meta">12:34 <span class="tg-sim-check">✓✓</span></div>
                        </div>
                    </div>
                </div>
                """
        else:
            profiles_html = """
            <div class="empty-state">
                <div class="empty-icon">📭</div>
                <h3>База пока пуста</h3>
                <p>Профили появятся здесь автоматически при первой публикации из клиента AyuGram.</p>
            </div>
            """

        dashboard_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SyncProfile Cloud Node</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #07090e;
            --bg-surface: rgba(16, 23, 38, 0.75);
            --bg-card: rgba(24, 34, 56, 0.6);
            --border-subtle: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(168, 85, 247, 0.3);
            --primary: #a855f7;
            --primary-glow: rgba(168, 85, 247, 0.4);
            --secondary: #06b6d4;
            --accent: #ec4899;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --amber: #f59e0b;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-base);
            color: var(--text-main);
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(168, 85, 247, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 85% 20%, rgba(6, 182, 212, 0.1) 0%, transparent 40%),
                radial-gradient(circle at 50% 80%, rgba(236, 72, 153, 0.08) 0%, transparent 50%);
            background-attachment: fixed;
            overflow-x: hidden;
            line-height: 1.5;
        }}

        .container {{
            max-width: 1240px;
            margin: 0 auto;
            padding: 2.5rem 1.5rem 4rem;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-subtle);
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .brand-icon {{
            width: 48px;
            height: 48px;
            border-radius: 14px;
            background: linear-gradient(135deg, #a855f7, #06b6d4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            box-shadow: 0 0 25px var(--primary-glow);
            animation: pulseGlow 3s ease-in-out infinite alternate;
        }}

        @keyframes pulseGlow {{
            0% {{ box-shadow: 0 0 15px rgba(168, 85, 247, 0.4); }}
            100% {{ box-shadow: 0 0 30px rgba(6, 182, 212, 0.6); }}
        }}

        .brand-title {{
            font-size: 1.75rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(to right, #ffffff, #c084fc, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .brand-subtitle {{
            font-size: 0.875rem;
            color: var(--text-muted);
            font-weight: 400;
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.45rem 0.9rem;
            border-radius: 9999px;
            font-size: 0.8125rem;
            font-weight: 500;
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            backdrop-filter: blur(8px);
        }}

        .status-pill.green {{
            color: #6ee7b7;
            border-color: rgba(16, 185, 129, 0.3);
            background: rgba(16, 185, 129, 0.1);
        }}

        .status-pill.amber {{
            color: #fcd34d;
            border-color: rgba(245, 158, 11, 0.3);
            background: rgba(245, 158, 11, 0.1);
        }}

        .dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: currentColor;
        }}

        .dot.pulse {{
            animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
        }}

        @keyframes ping {{
            75%, 100% {{
                transform: scale(2);
                opacity: 0;
            }}
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.55rem 1.1rem;
            border-radius: 10px;
            font-size: 0.875rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            border: 1px solid transparent;
        }}

        .btn-primary {{
            background: linear-gradient(135deg, #a855f7, #7c3aed);
            color: white;
            box-shadow: 0 4px 14px rgba(168, 85, 247, 0.35);
        }}

        .btn-primary:hover {{
            box-shadow: 0 6px 20px rgba(168, 85, 247, 0.5);
            transform: translateY(-1px);
        }}

        .btn-secondary {{
            background: var(--bg-surface);
            color: var(--text-main);
            border: 1px solid var(--border-subtle);
            backdrop-filter: blur(8px);
        }}

        .btn-secondary:hover {{
            border-color: var(--border-highlight);
            background: rgba(30, 41, 59, 0.9);
            transform: translateY(-1px);
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2.5rem;
        }}

        .stat-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            transition: transform 0.2s ease, border-color 0.2s ease;
            position: relative;
            overflow: hidden;
        }}

        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            opacity: 0.7;
        }}

        .stat-card:hover {{
            transform: translateY(-3px);
            border-color: var(--border-highlight);
        }}

        .stat-label {{
            font-size: 0.8125rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}

        .stat-value {{
            font-size: 2.25rem;
            font-weight: 800;
            letter-spacing: -1px;
            color: #ffffff;
            font-family: 'JetBrains Mono', monospace;
        }}

        .stat-sub {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.35rem;
        }}

        .nav-tabs {{
            display: flex;
            gap: 0.5rem;
            border-bottom: 1px solid var(--border-subtle);
            margin-bottom: 2rem;
        }}

        .tab-btn {{
            padding: 0.75rem 1.25rem;
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 0.9375rem;
            font-weight: 600;
            cursor: pointer;
            position: relative;
            transition: color 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .tab-btn:hover {{
            color: var(--text-main);
        }}

        .tab-btn.active {{
            color: #ffffff;
        }}

        .tab-btn.active::after {{
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, #a855f7, #06b6d4);
            border-radius: 2px;
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
            animation: fadeIn 0.25s ease-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}

        .search-box {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 0.6rem 1rem;
            width: 100%;
            max-width: 380px;
            backdrop-filter: blur(8px);
        }}

        .search-box:focus-within {{
            border-color: var(--border-highlight);
            box-shadow: 0 0 15px rgba(168, 85, 247, 0.2);
        }}

        .search-box input {{
            background: none;
            border: none;
            color: var(--text-main);
            font-size: 0.875rem;
            width: 100%;
            outline: none;
            font-family: inherit;
        }}

        .filter-tags {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}

        .filter-tag {{
            padding: 0.35rem 0.75rem;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 500;
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.15s ease;
        }}

        .filter-tag:hover, .filter-tag.active {{
            background: rgba(168, 85, 247, 0.15);
            border-color: rgba(168, 85, 247, 0.4);
            color: #c084fc;
        }}

        .profiles-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 1.25rem;
        }}

        .profile-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 1.25rem;
            backdrop-filter: blur(12px);
            transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
            position: relative;
        }}

        .profile-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(168, 85, 247, 0.35);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
        }}

        .profile-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}

        .profile-id-group {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .avatar-placeholder {{
            width: 42px;
            height: 42px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }}

        .profile-id {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9375rem;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}

        .copy-btn {{
            background: none;
            border: none;
            cursor: pointer;
            font-size: 0.8125rem;
            opacity: 0.6;
            transition: opacity 0.15s ease;
            padding: 2px;
        }}

        .copy-btn:hover {{
            opacity: 1;
        }}

        .profile-client {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.1rem;
        }}

        .premium-star {{
            color: #fbbf24;
            font-size: 1.125rem;
            animation: spinGlow 4s linear infinite;
        }}

        @keyframes spinGlow {{
            0% {{ transform: rotate(0deg); filter: drop-shadow(0 0 2px #fbbf24); }}
            50% {{ transform: rotate(180deg); filter: drop-shadow(0 0 6px #f59e0b); }}
            100% {{ transform: rotate(360deg); filter: drop-shadow(0 0 2px #fbbf24); }}
        }}

        .profile-colors {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }}

        .color-pill {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.35rem 0.6rem;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 600;
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .color-circle {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .profile-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-bottom: 1rem;
        }}

        .tag {{
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.25rem 0.55rem;
            border-radius: 6px;
            font-size: 0.6875rem;
            font-weight: 500;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-subtle);
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }}

        .tag.emoji {{
            color: #38bdf8;
            border-color: rgba(56, 189, 248, 0.25);
            background: rgba(56, 189, 248, 0.08);
        }}

        .tag.pattern {{
            color: #c084fc;
            border-color: rgba(192, 132, 252, 0.25);
            background: rgba(192, 132, 252, 0.08);
        }}

        .custom-badge-tag {{
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .tg-sim-wrapper {{
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid var(--border-subtle);
        }}

        .tg-sim-label {{
            font-size: 0.6875rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.4rem;
            font-weight: 600;
        }}

        .tg-sim-bubble {{
            background: #182533;
            border-radius: 10px;
            padding: 0.65rem 0.85rem;
            position: relative;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25);
        }}

        .tg-sim-author-row {{
            display: flex;
            align-items: center;
            gap: 0.35rem;
            margin-bottom: 0.3rem;
        }}

        .tg-sim-author {{
            font-size: 0.8125rem;
            font-weight: 700;
        }}

        .tg-sim-badge {{
            font-size: 0.6875rem;
            font-weight: 700;
            padding: 1px 4px;
            border-radius: 4px;
            border: 1px solid;
        }}

        .tg-sim-star {{
            font-size: 0.75rem;
            color: #fbbf24;
        }}

        .tg-sim-reply {{
            background: rgba(0, 0, 0, 0.2);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            margin-bottom: 0.35rem;
            font-size: 0.75rem;
        }}

        .tg-sim-reply-name {{
            font-weight: 600;
            font-size: 0.6875rem;
        }}

        .tg-sim-reply-text {{
            color: #8da0b3;
            font-size: 0.6875rem;
        }}

        .tg-sim-text {{
            font-size: 0.8125rem;
            color: #f5f5f5;
            display: flex;
            align-items: center;
            gap: 0.35rem;
            flex-wrap: wrap;
        }}

        .tg-sim-em-tag {{
            font-size: 0.6875rem;
            background: rgba(56, 189, 248, 0.2);
            color: #38bdf8;
            padding: 1px 5px;
            border-radius: 4px;
        }}

        .tg-sim-meta {{
            font-size: 0.625rem;
            color: #6c7883;
            text-align: right;
            margin-top: 0.15rem;
        }}

        .tg-sim-check {{
            color: #50b4f8;
            font-weight: bold;
        }}

        .empty-state {{
            grid-column: 1 / -1;
            text-align: center;
            padding: 4rem 1.5rem;
            background: var(--bg-surface);
            border: 1px dashed var(--border-subtle);
            border-radius: 16px;
        }}

        .empty-icon {{
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.7;
        }}

        .api-docs {{
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
        }}

        .api-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
            margin-top: 1rem;
        }}

        .api-table th {{
            text-align: left;
            padding: 0.75rem 1rem;
            background: rgba(255, 255, 255, 0.03);
            color: var(--text-muted);
            font-weight: 600;
            border-bottom: 1px solid var(--border-subtle);
        }}

        .api-table td {{
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-main);
        }}

        .method-badge {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 6px;
            font-size: 0.6875rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }}

        .method-get {{
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}

        .method-post {{
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }}

        .endpoint-code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8125rem;
            color: #c084fc;
        }}

        .curl-box {{
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #94a3b8;
            margin-top: 0.75rem;
            position: relative;
            overflow-x: auto;
            white-space: pre-wrap;
        }}

        .toast {{
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: #1e293b;
            color: #ffffff;
            padding: 0.85rem 1.25rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 500;
            border: 1px solid var(--border-highlight);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .toast.show {{
            transform: translateY(0);
            opacity: 1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <div class="brand-icon">🔄</div>
                <div>
                    <div class="brand-title">SyncProfile Node</div>
                    <div class="brand-subtitle">High-Performance Profile Synchronization Backend</div>
                </div>
            </div>
            <div class="header-actions">
                {auth_badge}
                <a href="/api/backup" class="btn btn-secondary" title="Скачать полный JSON бэкап">📥 Скачать бэкап</a>
                <button class="btn btn-primary" onclick="pingHealth()">⚡ Ping Node</button>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">👥 Синхронизировано профилей</div>
                <div class="stat-value">{stats.get("total_profiles", 0)}</div>
                <div class="stat-sub">Записей в локальной SQLite базе</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🔑 Активные сессии</div>
                <div class="stat-value">{stats.get("active_sessions", 0)}</div>
                <div class="stat-sub">Выдано Cookie токенов авторизации</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">⏱️ Время сервера (UTC)</div>
                <div class="stat-value" style="font-size: 1.4rem; padding-top: 0.4rem;">{datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")}</div>
                <div class="stat-sub">{datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🛡️ Протокол защиты</div>
                <div class="stat-value" style="font-size: 1.25rem; color: #34d399; padding-top: 0.4rem;">Cookie Auth</div>
                <div class="stat-sub">ID Spoofing Protection Active</div>
            </div>
        </div>

        <div class="nav-tabs">
            <button class="tab-btn active" onclick="switchTab('profiles', this)">
                👤 Профили ({len(all_profs)})
            </button>
            <button class="tab-btn" onclick="switchTab('api', this)">
                🔌 Документация API & Cookies
            </button>
            <button class="tab-btn" onclick="switchTab('client-guide', this)">
                📱 Подключение в AyuGram
            </button>
        </div>

        <div id="tab-profiles" class="tab-content active">
            <div class="toolbar">
                <div class="search-box">
                    <span>🔍</span>
                    <input type="text" id="searchInput" placeholder="Поиск по User ID или клиенту..." oninput="filterProfiles()">
                </div>
                <div class="filter-tags">
                    <button class="filter-tag active" onclick="filterByTag('all', this)">Все</button>
                    <button class="filter-tag" onclick="filterByTag('ayugram', this)">AyuGram</button>
                    <button class="filter-tag" onclick="filterByTag('exteragram', this)">exteraGram</button>
                    <button class="filter-tag" onclick="filterByTag('badge', this)">С бейджем</button>
                    <button class="filter-tag" onclick="filterByTag('emoji', this)">С эмодзи</button>
                </div>
            </div>

            <div class="profiles-grid" id="profilesGrid">
                {profiles_html}
            </div>
        </div>

        <div id="tab-api" class="tab-content">
            <div class="api-docs">
                <h2 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.75rem;">🔒 Авторизация и Cookies</h2>
                <p style="color: var(--text-muted); font-size: 0.875rem; margin-bottom: 1.5rem;">
                    Все эндпоинты синхронизации защищены и требуют наличия Cookie <code style="color: #c084fc;">{COOKIE_NAME}</code>.
                    Сессия создается при запросе <code style="color: #60a5fa;">POST /api/auth</code> или автоматически при первой публикации через <code style="color: #60a5fa;">POST /api/profile</code>.
                </p>

                <h3 style="font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem;">Эндпоинты API</h3>
                <table class="api-table">
                    <thead>
                        <tr>
                            <th>Метод</th>
                            <th>Эндпоинт</th>
                            <th>Доступ</th>
                            <th>Описание</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><span class="method-badge method-get">GET</span></td>
                            <td class="endpoint-code">/health</td>
                            <td>Публичный</td>
                            <td>Проверка статуса сервера, версии и времени</td>
                        </tr>
                        <tr>
                            <td><span class="method-badge method-get">GET</span></td>
                            <td class="endpoint-code">/api/profiles/all</td>
                            <td>Cookie</td>
                            <td>Полная выгрузка базы профилей для локальной синхронизации</td>
                        </tr>
                        <tr>
                            <td><span class="method-badge method-get">GET</span></td>
                            <td class="endpoint-code">/api/profiles/updates?since=TIMESTAMP</td>
                            <td>Cookie</td>
                            <td>Дельта-синхронизация (только профили, обновленные после указанного времени)</td>
                        </tr>
                        <tr>
                            <td><span class="method-badge method-get">GET</span></td>
                            <td class="endpoint-code">/api/profile/&#123;user_id&#125;</td>
                            <td>Cookie</td>
                            <td>Получение конкретного профиля по ID</td>
                        </tr>
                        <tr>
                            <td><span class="method-badge method-get">GET</span></td>
                            <td class="endpoint-code">/api/stats</td>
                            <td>Cookie</td>
                            <td>Расширенная статистика по профилям и сессиям</td>
                        </tr>
                        <tr>
                            <td><span class="method-badge method-get">GET</span></td>
                            <td class="endpoint-code">/api/backup</td>
                            <td>Cookie</td>
                            <td>Выгрузка полного структурированного JSON-файла бэкапа</td>
                        </tr>
                        <tr>
                            <td><span class="method-badge method-post">POST</span></td>
                            <td class="endpoint-code">/api/auth</td>
                            <td>Мастер-ключ</td>
                            <td>Аутентификация клиента и выдача сессионного Cookie</td>
                        </tr>
                        <tr>
                            <td><span class="method-badge method-post">POST</span></td>
                            <td class="endpoint-code">/api/profile</td>
                            <td>Cookie / Ключ</td>
                            <td>Публикация/обновление своего профиля (защита от ID Spoofing)</td>
                        </tr>
                        <tr>
                            <td><span class="method-badge method-post">POST</span></td>
                            <td class="endpoint-code">/api/profiles/batch</td>
                            <td>Cookie</td>
                            <td>Пакетный запрос до 500 профилей за один HTTP-вызов</td>
                        </tr>
                    </tbody>
                </table>

                <h3 style="font-size: 1rem; font-weight: 600; margin-top: 1.5rem; margin-bottom: 0.5rem;">Примеры запросов cURL</h3>
                <div class="curl-box">
curl -X POST https://sync.efn.mom/api/profile \\
  -H "Content-Type: application/json" \\
  -H "Cookie: {COOKIE_NAME}={SECRET_ACCESS_COOKIE if SECRET_ACCESS_COOKIE else 'YOUR_SESSION_TOKEN'}" \\
  -d '{{"user_id": 123456789, "premium": true, "name_color": 4, "profile_color": 5, "custom_badge": "VIP"}}'
                </div>
            </div>
        </div>

        <div id="tab-client-guide" class="tab-content">
            <div class="api-docs">
                <h2 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.75rem;">📱 Инструкция по настройке плагина AyuGram</h2>
                <div style="display: flex; flex-direction: column; gap: 1rem; margin-top: 1rem;">
                    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-subtle); padding: 1rem; border-radius: 10px;">
                        <h4 style="font-size: 0.9375rem; font-weight: 600; color: #c084fc; margin-bottom: 0.4rem;">1. Установка плагина</h4>
                        <p style="font-size: 0.8125rem; color: var(--text-muted);">
                            Откройте <strong>AyuGram &gt; Настройки &gt; Менеджер плагинов</strong> и импортируйте файл <code>sync.plugin</code> (или <code>sync_profile.plugin</code>).
                        </p>
                    </div>
                    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-subtle); padding: 1rem; border-radius: 10px;">
                        <h4 style="font-size: 0.9375rem; font-weight: 600; color: #38bdf8; margin-bottom: 0.4rem;">2. Автоматическая синхронизация</h4>
                        <p style="font-size: 0.8125rem; color: var(--text-muted);">
                            Плагин автоматически связывается с сервером по безопасному протоколу, запрашивает цвета участников диалогов и моментально обновляет оформление интерфейса без перезапуска приложения.
                        </p>
                    </div>
                    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-subtle); padding: 1rem; border-radius: 10px;">
                        <h4 style="font-size: 0.9375rem; font-weight: 600; color: #34d399; margin-bottom: 0.4rem;">3. Публикация своего профиля</h4>
                        <p style="font-size: 0.8125rem; color: var(--text-muted);">
                            В настройках плагина выберите цвета, узоры и бейдж для вашего аккаунта и нажмите <strong>«🚀 Опубликовать»</strong>. Все другие пользователи плагина увидят ваш кастомный профиль!
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">
        <span id="toastMsg">Уведомление</span>
    </div>

    <script>
        function switchTab(tabId, btn) {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + tabId).classList.add('active');
        }}

        function showToast(msg) {{
            const toast = document.getElementById('toast');
            document.getElementById('toastMsg').innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }}

        function copyText(text, btn) {{
            navigator.clipboard.writeText(text).then(() => {{
                const orig = btn.innerText;
                btn.innerText = '✅';
                showToast(`Скопировано: ${{text}}`);
                setTimeout(() => btn.innerText = orig, 1500);
            }}).catch(() => {{
                showToast(`ID: ${{text}}`);
            }});
        }}

        function filterProfiles() {{
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const cards = document.querySelectorAll('.profile-card');
            cards.forEach(card => {{
                const uid = card.getAttribute('data-uid').toLowerCase();
                const client = card.getAttribute('data-client').toLowerCase();
                if (uid.includes(query) || client.includes(query)) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        function filterByTag(tag, btn) {{
            document.querySelectorAll('.filter-tag').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            const cards = document.querySelectorAll('.profile-card');
            cards.forEach(card => {{
                if (tag === 'all') {{
                    card.style.display = 'block';
                }} else if (tag === 'ayugram') {{
                    card.style.display = card.getAttribute('data-client').includes('ayugram') ? 'block' : 'none';
                }} else if (tag === 'exteragram') {{
                    card.style.display = card.getAttribute('data-client').includes('extera') ? 'block' : 'none';
                }} else if (tag === 'badge') {{
                    card.style.display = card.getAttribute('data-badge') === '1' ? 'block' : 'none';
                }} else if (tag === 'emoji') {{
                    card.style.display = card.getAttribute('data-emoji') === '1' ? 'block' : 'none';
                }}
            }});
        }}

        async function pingHealth() {{
            const start = performance.now();
            try {{
                const resp = await fetch('/health');
                const data = await resp.json();
                const latency = (performance.now() - start).toFixed(1);
                showToast(`🟢 Сервер онлайн! Задержка: ${{latency}} ms`);
            }} catch (e) {{
                showToast('🔴 Ошибка подключения к серверу');
            }}
        }}
    </script>
</body>
</html>"""
        return dashboard_html

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
