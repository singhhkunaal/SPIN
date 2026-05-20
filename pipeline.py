from __future__ import annotations

import gc
import io
import tracemalloc

import openpyxl
from anthropic import Anthropic

import dashboard_export


# ---------------------------------------------------------
# Memory Tracking
# ---------------------------------------------------------
tracemalloc.start()


def log_memory(stage: str, status=None):
    current, peak = tracemalloc.get_traced_memory()

    msg = (
        f"🧠 MEMORY · {stage} · "
        f"Current={current/1024/1024:.1f}MB · "
        f"Peak={peak/1024/1024:.1f}MB"
    )

    print(msg, flush=True)

    if status:
        status(msg)

    gc.collect()


# ---------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------
def run_pipeline(
    uploaded_workbook_bytes,
    anthropic_api_key,
    supabase_url=None,
    supabase_key=None,
    status=None,
):

    if status:
        status("🚀 Starting pipeline")

    log_memory("Pipeline Start", status)

    # -----------------------------------------------------
    # Load Workbook
    # -----------------------------------------------------
    if status:
        status("📘 Loading workbook")

    workbook_stream = io.BytesIO(uploaded_workbook_bytes)

    wb = openpyxl.load_workbook(workbook_stream)

    log_memory("Workbook Loaded", status)

    # -----------------------------------------------------
    # Workbook Metadata
    # -----------------------------------------------------
    if status:
        status("📄 Reading workbook metadata")

    sheet_names = wb.sheetnames

    dashboard_data = {
        "workbook_name": "Diagnostic Template",
        "sheet_count": len(sheet_names),
        "sheets": sheet_names,
    }

    log_memory("Dashboard Payload Built", status)

    # -----------------------------------------------------
    # Claude Smoke Test
    # -----------------------------------------------------
    if status:
        status("🤖 Running Claude connectivity test")

    client = Anthropic(api_key=anthropic_api_key)

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=50,
        messages=[
            {
                "role": "user",
                "content": "Reply with: Claude connection successful",
            }
        ],
    )

    log_memory("Claude Call Complete", status)

    # -----------------------------------------------------
    # Save Workbook
    # -----------------------------------------------------
    if status:
        status("💾 Saving workbook")

    out_buf = io.BytesIO()

    wb.save(out_buf)

    log_memory("Workbook Save Complete", status)

    # -----------------------------------------------------
    # Final
    # -----------------------------------------------------
    if status:
        status("✅ Pipeline completed successfully")

    return (
        out_buf.getvalue(),
        "Treya_Output.xlsx",
        dashboard_data,
    )