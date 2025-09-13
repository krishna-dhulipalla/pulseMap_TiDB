from fastapi import APIRouter, Query
from sqlalchemy import text
from ..db.tidb import ENGINE
from openai import OpenAI
import json

router = APIRouter(prefix="/search", tags=["search"])
client = OpenAI()

def embed(q: str) -> list[float]:
    out = client.embeddings.create(model="text-embedding-3-small", input=[q])
    return out.data[0].embedding

@router.get("")
def search(q: str = Query(...), k: int = 10):
    qemb = embed(q)
    qvec = "[" + ",".join(f"{x:.7f}" for x in qemb) + "]"

    sql = text(f"""
        SELECT id, lat, lon, text, props, created_at,
               VEC_COSINE_DISTANCE(embedding, :qvec) AS dist
        FROM reports
        ORDER BY VEC_COSINE_DISTANCE(embedding, :qvec)
        LIMIT :k
    """)
    with ENGINE.begin() as cx:
        rows = cx.execute(sql, {"qvec": qvec, "k": int(k)}).fetchall()

    # shape as GeoJSON Features for your map
    feats = []
    for r in rows:
        rid, lat, lon, txt, props, created = r[:6]
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "properties": {
                "id": str(rid), "text": txt, "reported_at": str(created),
                **(json.loads(props or "{}"))
            },
        })
    return {"features": feats}
