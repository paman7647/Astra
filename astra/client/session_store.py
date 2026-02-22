# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
SessionStore — SQLite-backed local cache for fast Python-side reads.
Mirrors key data from the browser's IndexedDB for offline access,
faster queries, and persistent session metadata.
"""

import os
import json
import time
import sqlite3
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("Storage")


class SessionStore:
 """
 Lightweight SQLite-backed local cache.

 Provides instant Python-side reads for chats, contacts, and messages
 without requiring bridge round-trips to the browser.
 """

 SCHEMA_VERSION = 1

 def __init__(self, session_path: str):
  self._db_path = os.path.join(session_path, "astra_cache.db")
  self._conn: Optional[sqlite3.Connection] = None
  os.makedirs(session_path, exist_ok=True)

 # ── Lifecycle ──────────────────────────────────────────────

 def open(self):
  """Opens the SQLite connection and creates tables if needed."""
  self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
  self._conn.row_factory = sqlite3.Row
  self._conn.execute("PRAGMA journal_mode=WAL")
  self._conn.execute("PRAGMA synchronous=NORMAL")
  self._create_tables()
  logger.info(f"SessionStore opened: {self._db_path}")

 def close(self):
  """Closes the SQLite connection."""
  if self._conn:
   try:
    self._conn.close()
   except Exception:
    pass
   self._conn = None
   logger.debug("SessionStore closed.")

 def _create_tables(self):
  """Creates the cache schema."""
  c = self._conn
  c.executescript("""
   CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at REAL
   );

   CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY,
    name TEXT,
    unread_count INTEGER DEFAULT 0,
    last_message_ts REAL DEFAULT 0,
    is_group INTEGER DEFAULT 0,
    is_muted INTEGER DEFAULT 0,
    is_pinned INTEGER DEFAULT 0,
    is_archived INTEGER DEFAULT 0,
    msg_count INTEGER DEFAULT 0,
    raw_json TEXT,
    updated_at REAL
   );

   CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    name TEXT,
    is_my_contact INTEGER DEFAULT 0,
    is_business INTEGER DEFAULT 0,
    verified_name TEXT,
    raw_json TEXT,
    updated_at REAL
   );

   CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT,
    body TEXT,
    type TEXT DEFAULT 'chat',
    from_jid TEXT,
    to_jid TEXT,
    timestamp REAL,
    from_me INTEGER DEFAULT 0,
    ack INTEGER DEFAULT 0,
    has_media INTEGER DEFAULT 0,
    raw_json TEXT,
    updated_at REAL
   );

   CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id);
   CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp);
   CREATE INDEX IF NOT EXISTS idx_chats_ts ON chats(last_message_ts);
  """)
  # Store schema version
  self.set_meta("schema_version", str(self.SCHEMA_VERSION))
  c.commit()

 # ── Metadata ───────────────────────────────────────────────

 def set_meta(self, key: str, value: str):
  """Sets a metadata key-value pair."""
  self._conn.execute(
   "INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES (?, ?, ?)",
   (key, value, time.time())
  )
  self._conn.commit()

 def get_meta(self, key: str) -> Optional[str]:
  """Gets a metadata value by key."""
  row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
  return row["value"] if row else None

 def save_session_meta(self, session_id: str, phone: str, wa_version: str, pid: int):
  """Persists session metadata."""
  self.set_meta("session_id", session_id)
  self.set_meta("phone", phone)
  self.set_meta("wa_version", wa_version)
  self.set_meta("pid", str(pid))
  self.set_meta("started_at", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
  logger.debug("Session metadata saved to SQLite.")

 def get_session_info(self) -> Dict[str, Any]:
  """Returns all session metadata."""
  rows = self._conn.execute("SELECT key, value FROM meta").fetchall()
  return {r["key"]: r["value"] for r in rows}

 def clear_session_meta(self):
  """Clears session metadata on logout."""
  self._conn.execute("DELETE FROM meta WHERE key IN ('session_id', 'phone', 'wa_version', 'pid', 'started_at', 'session_cookies', 'session_ls')")
  self._conn.commit()

 def save_session_state(self, cookies: list, localStorage: dict):
  """Saves the encrypted-ready browser state for recovery."""
  self.set_meta("session_cookies", json.dumps(cookies))
  self.set_meta("session_ls", json.dumps(localStorage))
  logger.debug("Browser session state backed up to SQLite.")

 def get_session_state(self) -> dict:
  """Retrieves the last backed up browser state."""
  cookies_json = self.get_meta("session_cookies")
  ls_json = self.get_meta("session_ls")
  
  return {
   "cookies": json.loads(cookies_json) if cookies_json else [],
   "localStorage": json.loads(ls_json) if ls_json else {}
  }

 # ── Chat Operations ────────────────────────────────────────

 def upsert_chats(self, chats: List[Dict[str, Any]]):
  """Bulk upserts chat data from JS bridge."""
  now = time.time()
  self._conn.executemany(
   """INSERT OR REPLACE INTO chats
    (id, name, unread_count, last_message_ts, is_group, is_muted, is_pinned, is_archived, msg_count, raw_json, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
   [(
    c.get("id", ""),
    c.get("name", ""),
    c.get("unreadCount", 0),
    c.get("lastMessageTs", 0),
    int(c.get("isGroup", False)),
    int(c.get("isMuted", False)),
    int(c.get("isPinned", False)),
    int(c.get("isArchived", False)),
    c.get("msgCount", 0),
    json.dumps(c),
    now
   ) for c in chats]
  )
  self._conn.commit()

 def get_chats(self, limit: int = 100) -> List[Dict[str, Any]]:
  """Returns cached chats ordered by last message time."""
  rows = self._conn.execute(
   "SELECT * FROM chats ORDER BY last_message_ts DESC LIMIT ?", (limit,)
  ).fetchall()
  return [dict(r) for r in rows]

 def get_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
  """Returns a single cached chat."""
  row = self._conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
  return dict(row) if row else None

 # ── Contact Operations ─────────────────────────────────────

 def upsert_contacts(self, contacts: List[Dict[str, Any]]):
  """Bulk upserts contact data."""
  now = time.time()
  self._conn.executemany(
   """INSERT OR REPLACE INTO contacts
    (id, name, is_my_contact, is_business, verified_name, raw_json, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)""",
   [(
    c.get("id", ""),
    c.get("name", ""),
    int(c.get("isMyContact", False)),
    int(c.get("isBusiness", False)),
    c.get("verifiedName"),
    json.dumps(c),
    now
   ) for c in contacts]
  )
  self._conn.commit()

 def get_contacts(self, limit: int = 500) -> List[Dict[str, Any]]:
  """Returns cached contacts."""
  rows = self._conn.execute("SELECT * FROM contacts LIMIT ?", (limit,)).fetchall()
  return [dict(r) for r in rows]

 # ── Message Operations ─────────────────────────────────────

 def upsert_messages(self, messages: List[Dict[str, Any]]):
  """Bulk upserts message data."""
  now = time.time()
  self._conn.executemany(
   """INSERT OR REPLACE INTO messages
    (id, chat_id, body, type, from_jid, to_jid, timestamp, from_me, ack, has_media, raw_json, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
   [(
    m.get("id", ""),
    m.get("chatId", m.get("from", "")),
    m.get("body", ""),
    m.get("type", "chat"),
    m.get("from", ""),
    m.get("to", ""),
    m.get("timestamp", 0),
    int(m.get("fromMe", False)),
    m.get("ack", 0),
    int(m.get("hasMedia", False)),
    json.dumps(m),
    now
   ) for m in messages]
  )
  self._conn.commit()

 def get_messages(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
  """Returns cached messages for a chat."""
  rows = self._conn.execute(
   "SELECT * FROM messages WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
   (chat_id, limit)
  ).fetchall()
  return [dict(r) for r in rows]

 def search_messages(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
  """Full-text search across cached messages."""
  rows = self._conn.execute(
   "SELECT * FROM messages WHERE body LIKE ? ORDER BY timestamp DESC LIMIT ?",
   (f"%{query}%", limit)
  ).fetchall()
  return [dict(r) for r in rows]

 # ── Statistics ─────────────────────────────────────────────

 def get_stats(self) -> Dict[str, Any]:
  """Returns cache statistics."""
  chat_count = self._conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
  contact_count = self._conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
  msg_count = self._conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
  db_size = os.path.getsize(self._db_path) if os.path.exists(self._db_path) else 0

  return {
   "chats": chat_count,
   "contacts": contact_count,
   "messages": msg_count,
   "db_size_kb": round(db_size / 1024, 1),
   "db_path": self._db_path
  }

 def clear_all(self):
  """Wipes all cached data."""
  self._conn.executescript("""
   DELETE FROM chats;
   DELETE FROM contacts;
   DELETE FROM messages;
   DELETE FROM meta;
  """)
  logger.info("SessionStore cleared.")
