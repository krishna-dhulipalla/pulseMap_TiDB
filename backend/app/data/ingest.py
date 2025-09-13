from datetime import datetime, timezone
from openai import OpenAI
from sqlalchemy import text
from ..db.tidb import ENGINE
import json

client = OpenAI()  # uses OPENAI_API_KEY

EMBED_MODEL = "text-embedding-3-small"  # 1536-d

def embed(s: str) -> list[float]:
    out = client.embeddings.create(model=EMBED_MODEL, input=[s])
    return out.data[0].embedding  # list[float]

def insert_report(lat: float, lon: float, text_msg: str, props: dict | None = None):
    emb = embed(text_msg or "User report")
    created_at = datetime.now(timezone.utc).isoformat()
    props = props or {}
    vec_literal = "[" + ",".join(f"{x:.7f}" for x in emb) + "]"  # TiDB accepts '[...]'

    sql = text("""
        INSERT INTO reports (lat, lon, text, props, created_at, embedding)
        VALUES (:lat, :lon, :text, CAST(:props AS JSON), :created_at, :emb)
    """)
    with ENGINE.begin() as cx:
        cx.execute(sql, {
            "lat": float(lat),
            "lon": float(lon),
            "text": text_msg,
            "props": json.dumps(props),
            "created_at": created_at,
            "emb": vec_literal,
        })
