"""
Camada de persistência em banco de dados SQLite para armazenamento dos painéis publicados
e configurações operacionais (como o modo anti-hibernação para o dia do mutirão).
"""

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from slugify import slugify

from app.parser import parse_vagas_text

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "paineis.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS panels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                companies_json TEXT NOT NULL,
                total_companies INTEGER NOT NULL DEFAULT 0,
                total_jobs INTEGER NOT NULL DEFAULT 0,
                logo_data_url TEXT,
                right_logo_data_url TEXT,
                header_style TEXT NOT NULL DEFAULT 'dark',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # Migração automática segura caso a tabela já exista sem a coluna right_logo_data_url
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(panels)").fetchall()]
        if "right_logo_data_url" not in cols:
            conn.execute("ALTER TABLE panels ADD COLUMN right_logo_data_url TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.commit()


def get_keep_alive_enabled() -> bool:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'keep_alive_enabled'").fetchone()
        return bool(row and row["value"] == "1")


def set_keep_alive_enabled(enabled: bool) -> bool:
    init_db()
    val = "1" if enabled else "0"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES ('keep_alive_enabled', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (val,),
        )
        conn.commit()
    return enabled


def generate_unique_slug(title: str, conn: sqlite3.Connection) -> str:
    base = slugify(title or "painel-vagas", max_length=42)
    if not base:
        base = "painel-vagas"
    short_code = secrets.token_hex(3)
    candidate = f"{base}-{short_code}"
    while True:
        row = conn.execute("SELECT 1 FROM panels WHERE slug = ?", (candidate,)).fetchone()
        if not row:
            return candidate
        short_code = secrets.token_hex(3)
        candidate = f"{base}-{short_code}"


def save_or_update_panel(
    title: str,
    raw_text: str,
    slug: Optional[str] = None,
    logo_data_url: Optional[str] = None,
    right_logo_data_url: Optional[str] = None,
    header_style: str = "dark",
) -> Dict[str, Any]:
    """
    Cria um novo painel publicado ou atualiza um painel existente mantendo o mesmo slug.
    """
    init_db()
    parsed = parse_vagas_text(raw_text)
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_title = (title or "MUTIRÃO EMPREGA | CASA DO TRABALHADOR").strip()

    with get_connection() as conn:
        existing = None
        if slug:
            existing = conn.execute(
                "SELECT * FROM panels WHERE slug = ?", (slug.strip(),)
            ).fetchone()

        if existing:
            final_logo = logo_data_url if logo_data_url is not None else existing["logo_data_url"]
            # Para right_logo_data_url: string vazia "" remove a logo direita; None mantém; data:... substitui
            if right_logo_data_url == "":
                final_right_logo = None
            elif right_logo_data_url is not None:
                final_right_logo = right_logo_data_url
            else:
                final_right_logo = existing["right_logo_data_url"]

            conn.execute(
                """
                UPDATE panels
                SET title = ?,
                    raw_text = ?,
                    companies_json = ?,
                    total_companies = ?,
                    total_jobs = ?,
                    logo_data_url = ?,
                    right_logo_data_url = ?,
                    header_style = ?,
                    updated_at = ?
                WHERE slug = ?
                """,
                (
                    clean_title,
                    raw_text,
                    json.dumps(parsed["companies"], ensure_ascii=False),
                    parsed["total_companies"],
                    parsed["total_jobs"],
                    final_logo,
                    final_right_logo,
                    header_style or existing["header_style"] or "dark",
                    now_iso,
                    existing["slug"],
                ),
            )
            conn.commit()
            target_slug = existing["slug"]
        else:
            target_slug = slug.strip() if (slug and slug.strip()) else generate_unique_slug(clean_title, conn)
            final_right_logo = right_logo_data_url if right_logo_data_url else None
            conn.execute(
                """
                INSERT INTO panels (
                    slug, title, raw_text, companies_json,
                    total_companies, total_jobs, logo_data_url,
                    right_logo_data_url, header_style, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    target_slug,
                    clean_title,
                    raw_text,
                    json.dumps(parsed["companies"], ensure_ascii=False),
                    parsed["total_companies"],
                    parsed["total_jobs"],
                    logo_data_url,
                    final_right_logo,
                    header_style or "dark",
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()

        return get_panel_by_slug(target_slug)  # type: ignore


def get_panel_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM panels WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return None
        return _row_to_dict(row)


def list_recent_panels(limit: int = 20) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM panels ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "slug": row["slug"],
        "title": row["title"],
        "raw_text": row["raw_text"],
        "companies": json.loads(row["companies_json"]),
        "total_companies": row["total_companies"],
        "total_jobs": row["total_jobs"],
        "logo_data_url": row["logo_data_url"],
        "right_logo_data_url": row["right_logo_data_url"] if "right_logo_data_url" in row.keys() else None,
        "header_style": row["header_style"] or "dark",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
