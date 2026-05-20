from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path


OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)



def save_dashboard_json(data: dict) -> str:
    dashboard_id = str(uuid.uuid4())[:12]

    payload = {
        "dashboard_id": dashboard_id,
        "created_at": datetime.utcnow().isoformat(),
        "data": data,
    }

    out_path = OUTPUT_DIR / f"dashboard_{dashboard_id}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    return dashboard_id
