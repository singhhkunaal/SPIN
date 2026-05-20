"""
Supabase-backed cache layer.
Replaces the four JSON memory files from the original script:
  - vendor_memory.json           -> vendor_dedupe_memory table
  - vendor_map_memory.json       -> vendor_map_memory table
  - company_research_memory.json -> company_research_memory table
  - savings_benchmarks_memory.json -> savings_benchmarks_memory table

Every function tolerates Supabase being unreachable — it just degrades to
no caching rather than crashing the pipeline.
"""

from __future__ import annotations
from typing import Optional
from supabase import Client, create_client


def get_client(url: str, key: str) -> Client:
    """Create a Supabase client. Call once and pass around."""
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Vendor dedupe cache
# Schema: (vendor_key TEXT PK, standard_name, parent, notes, confidence_score)
# ---------------------------------------------------------------------------
def load_vendor_dedupe_memory(client: Optional[Client]) -> dict:
    if client is None:
        return {}
    try:
        res = client.table("vendor_dedupe_memory").select("*").execute()
        return {
            row["vendor_key"]: {
                "standard_name": row.get("standard_name", ""),
                "parent": row.get("parent", ""),
                "notes": row.get("notes", ""),
                "confidence_score": row.get("confidence_score", "Requires Review"),
            }
            for row in (res.data or [])
        }
    except Exception as e:
        print(f"  ⚠️ Could not load vendor_dedupe_memory: {e}")
        return {}


def save_vendor_dedupe_batch(client: Optional[Client], batch: dict) -> None:
    """batch: {vendor_key: {standard_name, parent, notes, confidence_score}}"""
    if client is None or not batch:
        return
    try:
        rows = [
            {
                "vendor_key": k,
                "standard_name": v.get("standard_name", ""),
                "parent": v.get("parent", ""),
                "notes": v.get("notes", ""),
                "confidence_score": v.get("confidence_score", "Requires Review"),
            }
            for k, v in batch.items()
        ]
        client.table("vendor_dedupe_memory").upsert(rows, on_conflict="vendor_key").execute()
    except Exception as e:
        print(f"  ⚠️ Could not save vendor_dedupe_memory: {e}")


# ---------------------------------------------------------------------------
# Vendor map cache
# Schema: (vendor_key TEXT PK, area_mapping, category_mapping, notes, confidence_score)
# ---------------------------------------------------------------------------
def load_vendor_map_memory(client: Optional[Client]) -> dict:
    if client is None:
        return {}
    try:
        res = client.table("vendor_map_memory").select("*").execute()
        return {
            row["vendor_key"]: {
                "area_mapping": row.get("area_mapping", "Requires Review"),
                "category_mapping": row.get("category_mapping", "Requires Review"),
                "notes": row.get("notes", ""),
                "confidence_score": row.get("confidence_score", "Requires Review"),
            }
            for row in (res.data or [])
        }
    except Exception as e:
        print(f"  ⚠️ Could not load vendor_map_memory: {e}")
        return {}


def save_vendor_map_batch(client: Optional[Client], batch: dict) -> None:
    if client is None or not batch:
        return
    try:
        rows = [
            {
                "vendor_key": k,
                "area_mapping": v.get("area_mapping", "Requires Review"),
                "category_mapping": v.get("category_mapping", "Requires Review"),
                "notes": v.get("notes", ""),
                "confidence_score": v.get("confidence_score", "Requires Review"),
            }
            for k, v in batch.items()
        ]
        client.table("vendor_map_memory").upsert(rows, on_conflict="vendor_key").execute()
    except Exception as e:
        print(f"  ⚠️ Could not save vendor_map_memory: {e}")


# ---------------------------------------------------------------------------
# Company research cache
# Schema: (research_key TEXT PK, research_text TEXT)
# ---------------------------------------------------------------------------
def load_research(client: Optional[Client], key: str) -> Optional[str]:
    if client is None:
        return None
    try:
        res = client.table("company_research_memory").select("*").eq("research_key", key).execute()
        if res.data:
            return res.data[0].get("research_text")
        return None
    except Exception as e:
        print(f"  ⚠️ Could not load research for {key}: {e}")
        return None


def save_research(client: Optional[Client], key: str, text: str) -> None:
    if client is None:
        return
    try:
        client.table("company_research_memory").upsert(
            {"research_key": key, "research_text": text},
            on_conflict="research_key",
        ).execute()
    except Exception as e:
        print(f"  ⚠️ Could not save research for {key}: {e}")


# ---------------------------------------------------------------------------
# Savings benchmarks cache
# Schema: (category TEXT PK, addressability, savings_low_pct, savings_high_pct, notes)
# ---------------------------------------------------------------------------
def load_savings_benchmarks(client: Optional[Client]) -> dict:
    if client is None:
        return {}
    try:
        res = client.table("savings_benchmarks_memory").select("*").execute()
        out: dict = {}
        for row in (res.data or []):
            strategy = row.get("strategy_json")
            if isinstance(strategy, str):
                try:
                    import json as _json
                    strategy = _json.loads(strategy) if strategy else {}
                except Exception:
                    strategy = {}
            elif strategy is None:
                strategy = {}
            out[row["category"]] = {
                "addressability": float(row.get("addressability") or 0.8),
                "savings_low_pct": float(row.get("savings_low_pct") or 0.01),
                "savings_high_pct": float(row.get("savings_high_pct") or 0.02),
                "notes": row.get("notes", ""),
                "strategy": strategy,
            }
        return out
    except Exception as e:
        print(f"  ⚠️ Could not load savings_benchmarks: {e}")
        return {}


def save_savings_benchmarks(client: Optional[Client], batch: dict) -> None:
    if client is None or not batch:
        return
    try:
        import json as _json
        rows = []
        for k, v in batch.items():
            strategy = v.get("strategy") or {}
            rows.append({
                "category": k,
                "addressability": v.get("addressability", 0.8),
                "savings_low_pct": v.get("savings_low_pct", 0.01),
                "savings_high_pct": v.get("savings_high_pct", 0.02),
                "notes": v.get("notes", ""),
                "strategy_json": _json.dumps(strategy) if strategy else None,
            })
        client.table("savings_benchmarks_memory").upsert(rows, on_conflict="category").execute()
    except Exception as e:
        print(f"  ⚠️ Could not save savings_benchmarks: {e}")
