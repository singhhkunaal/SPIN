from __future__ import annotations
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1200,
            "messages": [
                {
                    "role": "user",
                    "content": research_prompt,
                }
            ],
        },
        label="Research",
        status=status,
    )

    research_summary = ""

    try:
        research_summary = research_response.content[0].text
    except Exception:
        research_summary = "Research unavailable"

    log_memory("Company Research Complete", status)

    # ---------------------------------------------------------
    # Dashboard Generation
    # ---------------------------------------------------------
    if status:
        status("📊 Building dashboard payload")

    dashboard_data = dashboard_export.build_ironclad_data(
        deduped,
        benchmarks,
        research_summary,
    )

    log_memory("Dashboard Payload Built", status)

    # ---------------------------------------------------------
    # Workbook Save
    # ---------------------------------------------------------
    if status:
        status("💾 Saving workbook")

    log_memory("Before Workbook Save", status)

    out_buf = io.BytesIO()

    wb.save(out_buf)

    log_memory("Workbook Save Complete", status)

    # ---------------------------------------------------------
    # Final Output
    # ---------------------------------------------------------
    suggested_filename = "Treya_Completed_Diagnostic.xlsx"

    if status:
        status("✅ Pipeline completed successfully")

    return (
        out_buf.getvalue(),
        suggested_filename,
        dashboard_data,
    )
