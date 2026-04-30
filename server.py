import os
import json
from functools import lru_cache
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="subject_guess_proto")
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Optional: put ADM1.geojson next to server.py to use real regional polygons.
# Expected common fields: shapeGroup/ADM0_A3/iso3 = RUS, shapeName/name/NAME_1 = region name.
ADM1_PATH = os.getenv("ADM1_PATH", os.path.join(BASE_DIR, "ADM1.geojson"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@lru_cache(maxsize=1)
def _load_adm1_index() -> Dict[str, Any]:
    if not os.path.exists(ADM1_PATH):
        return {"by_country": {}}

    with open(ADM1_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    feats = data.get("features") or []
    by_country: Dict[str, list] = {}
    for ft in feats:
        props = (ft or {}).get("properties") or {}
        code = (
            props.get("shapeGroup")
            or props.get("ADM0_A3")
            or props.get("iso3")
            or props.get("ISO_A3")
            or ""
        ).strip().upper()
        if not code:
            continue
        by_country.setdefault(code, []).append(ft)
    return {"by_country": by_country}


@app.get("/adm1/{a3}")
def adm1_for_country(a3: str):
    a3 = (a3 or "").strip().upper()
    feats = _load_adm1_index().get("by_country", {}).get(a3, [])
    return JSONResponse({"type": "FeatureCollection", "features": feats})


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
