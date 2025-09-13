from __future__ import annotations
import os, json, math, time, argparse
from typing import List, Tuple
from pathlib import Path
from tqdm import tqdm
import sqlite3
from sqlalchemy import create_engine, text
from openai import OpenAI

# --- Config ---
EMBED_MODEL = "text-embedding-3-small"   # 1536-d
BATCH_ROWS  = 100                         # rows per DB batch
BATCH_EMB   = 64                          # texts per embed API call

def get_args():
    ap = argparse.ArgumentParser("Seed TiDB from local SQLite reports")
    ap.add_argument("--sqlite", default=None,
                    help="Path to SQLite DB; default=backend/app/data/pulsemaps_reports.db (from settings)")
    return ap.parse_args()

def resolve_sqlite_path(cli_path: str | None) -> Path:
    if cli_path:
        return Path(cli_path).resolve()
    # fall back to your project default structure
    # matches earlier code: /data/pulsemaps_reports.db in HF or repo/data locally
    candidates = [
        Path("./data/pulsemaps_reports.db"),
        Path("backend/app/data/pulsemaps_reports.db"),
        Path("/data/pulsemaps_reports.db"),
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    raise FileNotFoundError("Could not find SQLite DB. Pass --sqlite /path/to.db")

def ensure_tidb_schema(engine):
    ddl = """
    CREATE TABLE IF NOT EXISTS reports (
      id BIGINT PRIMARY KEY,
      lat DOUBLE,
      lon DOUBLE,
      text TEXT,
      props JSON,
      created_at TIMESTAMP NULL,
      embedding VECTOR(1536)
    );
    CREATE VECTOR INDEX IF NOT EXISTS idx_reports_embed
    ON reports ((VEC_COSINE_DISTANCE(embedding))) USING HNSW;
    """
    with engine.begin() as cx:
        for stmt in ddl.strip().split(";"):
            s = stmt.strip()
            if s:
                cx.execute(text(s))

def fetch_sqlite_rows(conn: sqlite3.Connection, last_id: int, limit: int) -> List[Tuple]:
    # Your SQLite schema: id, lat, lon, text, props_json, created_at
    cur = conn.execute(
        "SELECT id, lat, lon, text, props_json, created_at FROM reports "
        "WHERE id > ? ORDER BY id ASC LIMIT ?",
        (last_id, limit),
    )
    return cur.fetchall()

def embed_batch(client: OpenAI, texts: List[str]) -> List[List[float]]:
    # batch to reduce roundtrips
    out = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in out.data]

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def main():
    tidb_url = os.getenv("TIDB_URL")
    if not tidb_url:
        raise RuntimeError("TIDB_URL env not set")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY env not set")

    args = get_args()
    sqlite_path = resolve_sqlite_path(args.sqlite)

    # Connect
    engine = create_engine(tidb_url, pool_pre_ping=True)
    ensure_tidb_schema(engine)

    sconn = sqlite3.connect(str(sqlite_path))
    sconn.row_factory = sqlite3.Row

    # Find the last migrated id in TiDB
    with engine.begin() as cx:
        row = cx.execute(text("SELECT COALESCE(MAX(id), 0) FROM reports")).fetchone()
        last_id = int(row[0] or 0)

    print(f"Starting from id > {last_id} (SQLite: {sqlite_path})")

    total_inserted = 0
    with engine.begin() as cx:
        # quick count just for progress (optional)
        row = sconn.execute("SELECT COUNT(*) FROM reports WHERE id > ?", (last_id,)).fetchone()
        todo = int(row[0] or 0)

    # Main loop
    pbar = tqdm(total=todo, desc="Migrating", unit="rows")
    client = OpenAI()

    while True:
        rows = fetch_sqlite_rows(sconn, last_id, BATCH_ROWS)
        if not rows:
            break

        # Build embeddings in small batches
        texts = [ (r["text"] or "User report") for r in rows ]
        embs: List[List[float]] = []
        for chunk in chunked(texts, BATCH_EMB):
            # simple retry on rate limit
            for attempt in range(4):
                try:
                    embs.extend(embed_batch(client, chunk))
                    break
                except Exception as e:
                    if attempt == 3:
                        raise
                    time.sleep(1.5 * (attempt + 1))

        # Prepare batched inserts
        values = []
        for r, emb in zip(rows, embs):
            rid = int(r["id"])
            lat = float(r["lat"]) if r["lat"] is not None else None
            lon = float(r["lon"]) if r["lon"] is not None else None
            txt = r["text"] or ""
            props = r["props_json"] or "{}"
            created = r["created_at"]  # ISO string in your schema

            vec_literal = "[" + ",".join(f"{x:.7f}" for x in emb) + "]"  # TiDB vector literal

            values.append({
                "id": rid, "lat": lat, "lon": lon, "text": txt,
                "props": props, "created_at": created, "emb": vec_literal
            })

        # INSERT ... ON DUPLICATE KEY UPDATE to be idempotent
        sql = text("""
            INSERT INTO reports (id, lat, lon, text, props, created_at, embedding)
            VALUES (:id, :lat, :lon, :text, CAST(:props AS JSON), :created_at, :emb)
            ON DUPLICATE KEY UPDATE
              lat=VALUES(lat), lon=VALUES(lon), text=VALUES(text),
              props=VALUES(props), created_at=VALUES(created_at),
              embedding=VALUES(embedding)
        """)
        with engine.begin() as cx:
            cx.execute(sql, values)

        last_id = int(rows[-1]["id"])
        total_inserted += len(rows)
        pbar.update(len(rows))

    pbar.close()
    print(f"Done. Migrated/updated {total_inserted} rows into TiDB.")

if __name__ == "__main__":
    main()
