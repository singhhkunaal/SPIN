"""
dashboard_export.py
===================
Transforms pipeline outputs into the IRONCLAD-shaped data structure that the
Claude-designed React dashboard expects (window.IRONCLAD).

This module is called from pipeline.py at the end of run_pipeline, replacing
the simpler `dashboard_data` block that existed in the first version.
"""

from __future__ import annotations
import re
from collections import defaultdict
from datetime import datetime, date
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Helpers for header-based column lookup
# ---------------------------------------------------------------------------
def _find_column(ws, header_row: int, candidates: list[str]) -> Optional[int]:
    """Find a column index whose header contains any of the candidate strings."""
    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=header_row, column=col_idx)
        if cell.value is None:
            continue
        h = str(cell.value).strip().lower()
        for cand in candidates:
            if cand.lower() in h:
                return col_idx
    return None


def _parse_month(date_val) -> Optional[str]:
    """Coerce a cell value into YYYY-MM, or None if unparseable."""
    if date_val is None:
        return None
    if isinstance(date_val, (datetime, date)):
        return date_val.strftime("%Y-%m")
    try:
        s = str(date_val).strip()[:10]
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m")
            except ValueError:
                continue
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Monthly extraction from Consolidated Data
# ---------------------------------------------------------------------------
def extract_monthly_per_vendor(ws_cd, cd_last_row: int, status: Callable[[str], None]) -> dict:
    """
    Reads Consolidated Data row by row and returns:
      {
        "raw_vendor_monthly": { raw_vendor_name: { "YYYY-MM": spend, ... } },
        "raw_vendor_txns":    { raw_vendor_name: int },
        "all_months":         set("YYYY-MM"),
      }

    Uses header-based column detection so the column positions don't need to
    be hardcoded. Falls back to defaults (vendor=col D, date=col H, spend=col G)
    if headers can't be matched — these match the Treya diagnostic template.
    """
    header_row = 5  # standard Treya template header row
    vendor_col = _find_column(ws_cd, header_row, ["original vendor", "vendor name", "vendor"])
    date_col   = _find_column(ws_cd, header_row, ["date", "invoice date", "txn date"])
    spend_col  = _find_column(ws_cd, header_row, ["total amount", "amount", "spend", "total"])

    # Fall back to known positions in the standard Treya template
    if vendor_col is None: vendor_col = 4   # col D
    if date_col   is None: date_col   = 8   # col H
    if spend_col  is None: spend_col  = 7   # col G

    status(f"  📅 Monthly extraction: vendor=col {vendor_col}, date=col {date_col}, spend=col {spend_col}")

    raw_vendor_monthly: dict = defaultdict(lambda: defaultdict(float))
    raw_vendor_txns: dict = defaultdict(int)
    all_months: set = set()
    rows_skipped_no_date = 0
    rows_skipped_no_spend = 0
    rows_used = 0

    for row_idx in range(6, cd_last_row + 1):
        vendor = ws_cd.cell(row=row_idx, column=vendor_col).value
        if not vendor:
            continue
        vendor = str(vendor).strip()

        spend_val = ws_cd.cell(row=row_idx, column=spend_col).value
        if not isinstance(spend_val, (int, float)):
            rows_skipped_no_spend += 1
            continue

        date_val = ws_cd.cell(row=row_idx, column=date_col).value
        month_key = _parse_month(date_val)
        if month_key is None:
            rows_skipped_no_date += 1
            # Still count the txn but skip monthly bucketing
            raw_vendor_txns[vendor] += 1
            continue

        raw_vendor_monthly[vendor][month_key] += float(spend_val)
        raw_vendor_txns[vendor] += 1
        all_months.add(month_key)
        rows_used += 1

    status(f"  📅 Monthly: {rows_used} rows bucketed · "
           f"{rows_skipped_no_date} no-date · {rows_skipped_no_spend} no-spend · "
           f"{len(all_months)} unique months")

    return {
        "raw_vendor_monthly": dict(raw_vendor_monthly),
        "raw_vendor_txns": dict(raw_vendor_txns),
        "all_months": all_months,
    }


def select_12_months(all_months: set) -> list[str]:
    """Sort all months and return up to the last 12 in chronological order."""
    if not all_months:
        return []
    sorted_months = sorted(all_months)
    return sorted_months[-12:]


# ---------------------------------------------------------------------------
# Research text parser
# ---------------------------------------------------------------------------
SECTION_HEADER_RE = re.compile(r"^\s*(\d+)\.\s*([A-Z][^\n]*?)\s*$")


def parse_research_sections(research_text: str) -> list[dict]:
    """
    Parse research_summary plaintext into a list of section dicts that match
    the dashboard's research.sections[] shape:
        { title, number, kind, body, bullets? }

    The current research prompt produces output in this format:
        1. COMPANY OVERVIEW
        body text...

        2. INDUSTRY AND SECTOR
        body text...

    Lines like "- bullet item" or numeric "5. Foo" inside a section become bullets.
    """
    if not research_text:
        return []

    sections: list[dict] = []
    current: Optional[dict] = None
    body_lines: list[str] = []
    bullets: list[str] = []

    def flush():
        nonlocal current, body_lines, bullets
        if current is None:
            return
        body = " ".join(l.strip() for l in body_lines if l.strip())
        current["body"] = body
        if bullets:
            current["bullets"] = bullets[:]
        sections.append(current)
        current = None
        body_lines = []
        bullets = []

    for raw_line in research_text.split("\n"):
        line = raw_line.rstrip()
        if not line.strip():
            continue

        m = SECTION_HEADER_RE.match(line)
        if m:
            flush()
            num, title = m.group(1), m.group(2).strip()
            # Title-case the section title (currently UPPERCASE from the prompt)
            pretty = title.title().replace(" And ", " & ").replace(" Cogs", " COGS").replace(" Pe ", " PE ")
            current = {
                "title": pretty,
                "number": num.zfill(2),
                "kind": "sourced",  # default; the pipeline doesn't currently distinguish
                "body": "",
            }
            continue

        # Inside a section
        if current is None:
            continue

        stripped = line.strip()
        # Detect bullet-style lines (starts with -, •, or digits like "1.", "1)")
        if (stripped.startswith(("-", "•", "*"))
                or re.match(r"^\d+[\.\)]\s+", stripped)):
            bullet = re.sub(r"^[-•*]\s*", "", stripped)
            bullet = re.sub(r"^\d+[\.\)]\s+", "", bullet)
            if bullet:
                bullets.append(bullet)
        else:
            # Treat "Heading:" lines as a soft sub-heading that becomes body
            body_lines.append(stripped)

    flush()
    return sections


# ---------------------------------------------------------------------------
# THE big builder: assemble IRONCLAD-shaped data
# ---------------------------------------------------------------------------
def build_ironclad_data(
    *,
    ws_cd,
    cd_last_row: int,
    company_name: str,
    pe_firm: str,
    industry: str,
    research_summary: str,
    unique_vendors: list,
    get_canonical,                       # callable raw -> canonical
    vendor_memory: dict,                 # canonical -> {standard_name, parent, notes, ...}
    vendor_map_memory: dict,             # standard_name -> {area_mapping, category_mapping, ...}
    vendor_spend: dict,                  # raw_vendor -> total spend (annual)
    benchmarks: dict,                    # category -> {addressability, savings_low_pct, savings_high_pct, notes, strategy?}
    total_raw_spend: float,
    status: Callable[[str], None],
) -> dict:
    """
    Returns the IRONCLAD-shaped data dict that the dashboard expects on
    window.IRONCLAD. See ironclad-data.js for the exact structure.
    """
    # ---- 1. Monthly bucketing from raw transactions ----
    monthly_info = extract_monthly_per_vendor(ws_cd, cd_last_row, status)
    raw_vendor_monthly = monthly_info["raw_vendor_monthly"]
    raw_vendor_txns = monthly_info["raw_vendor_txns"]
    months = select_12_months(monthly_info["all_months"])
    if not months:
        # Fallback: invent 12 months ending at current month
        today = datetime.today()
        months = []
        y, m = today.year, today.month
        for _ in range(12):
            months.append(f"{y:04d}-{m:02d}")
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        months.reverse()

    month_index = {m: i for i, m in enumerate(months)}
    txn_count_total = sum(raw_vendor_txns.values())

    # ---- 2. Aggregate raw vendors -> deduped/standardized vendors ----
    # Build standardized vendor records by collapsing all raws that map to the
    # same standard_name (via canonical lookup, then dedupe enrichment).
    std_vendors: dict = {}

    for raw_vendor in unique_vendors:
        canonical = get_canonical(raw_vendor)
        std_name = vendor_memory.get(canonical, {}).get("standard_name", canonical)
        mapping = vendor_map_memory.get(std_name, {})
        area = mapping.get("area_mapping", "Requires Review") or "Requires Review"
        category = mapping.get("category_mapping", "Requires Review") or "Requires Review"

        rec = std_vendors.setdefault(std_name, {
            "name": std_name,
            "area": area,
            "category": category,
            "spend": 0.0,
            "txns": 0,
            "monthly": [0.0] * len(months),
        })
        # Once the area/category is set from the first raw, keep it stable
        # (raws collapsing into the same std_name *should* have matching mapping)
        rec["spend"] += vendor_spend.get(raw_vendor, 0.0)
        rec["txns"]  += raw_vendor_txns.get(raw_vendor, 0)

        # Distribute monthly bucket
        for ym, amount in raw_vendor_monthly.get(raw_vendor, {}).items():
            idx = month_index.get(ym)
            if idx is not None:
                rec["monthly"][idx] += amount

    # Sort by spend descending and assign v001…vNNN IDs
    sorted_std = sorted(std_vendors.values(), key=lambda r: r["spend"], reverse=True)
    vendors_out: list[dict] = []
    for i, rec in enumerate(sorted_std, start=1):
        vendors_out.append({
            "id": f"v{i:03d}",
            "name": rec["name"],
            "area": rec["area"],
            "category": rec["category"],
            "spend": round(rec["spend"], 2),
            "txns": rec["txns"],
            "monthly": [round(v, 2) for v in rec["monthly"]],
        })

    status(f"  📤 IRONCLAD vendors built: {len(vendors_out)} standardized vendors")

    # ---- 3. Savings model ----
    savings_model: list[dict] = []
    for category, bm in benchmarks.items():
        entry = {
            "category": category,
            "addressable": float(bm.get("addressability", 0.0)),
            "savingsLow":  float(bm.get("savings_low_pct", 0.0)),
            "savingsHigh": float(bm.get("savings_high_pct", 0.0)),
            "note":        bm.get("notes", ""),
        }
        if bm.get("strategy"):
            # Strategy may be stored as JSON-stringified dict or dict already
            s = bm["strategy"]
            if isinstance(s, str):
                try:
                    import json as _json
                    s = _json.loads(s)
                except Exception:
                    s = None
            if isinstance(s, dict):
                entry["strategy"] = {
                    "headline": s.get("headline", ""),
                    "levers":   s.get("levers", []),
                    "timeline": s.get("timeline", ""),
                }
        savings_model.append(entry)

    # ---- 4. Research sections ----
    research_sections = parse_research_sections(research_summary)

    # Date label for the source string
    if months:
        first_m, last_m = months[0], months[-1]
        def _label(ym):
            y, m = ym.split("-")
            return datetime(int(y), int(m), 1).strftime("%b %y")
        source_label = f"{_label(first_m)} — {_label(last_m)} Vendor Spend Detail"
    else:
        source_label = "Vendor Spend Detail"

    # ---- 5. Assemble final IRONCLAD object ----
    ironclad = {
        "client": company_name,
        "source": source_label,
        "months": months,
        "totalSpend": round(total_raw_spend, 2),
        "txnCount":   txn_count_total,
        "vendors":    vendors_out,
        "savingsModel": savings_model,
        "research": {
            "name":         company_name,
            "peFirm":       pe_firm or "Not specified",
            "industry":     industry if industry and industry != "Unknown" else "Not specified",
            "researchDate": datetime.today().strftime("%Y-%m-%d"),
            "caveat":       "",  # Optional; populated by the prompt if needed
            "sections":     research_sections,
        },
    }
    return ironclad
