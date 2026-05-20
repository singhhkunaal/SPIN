from __future__ import annotations

import traceback

import streamlit as st

import pipeline
import storage


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Treya Spend Diagnostic",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Treya Spend Diagnostic")
    st.caption("AP analysis & savings opportunity tool")

    st.divider()

    api_status = (
        "✅ Connected"
        if st.secrets.get("CLAUDE_API_KEY")
        else "❌ Missing"
    )

    supa_status = (
        "✅ Connected"
        if st.secrets.get("SUPABASE_URL")
        and st.secrets.get("SUPABASE_KEY")
        else "⚠️ Not configured"
    )

    st.caption(f"Anthropic API: {api_status}")
    st.caption(f"Supabase: {supa_status}")


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
st.title("Treya Spend Diagnostic")

st.caption(
    "Upload a populated diagnostic template, run AI enrichment, "
    "and download the completed workbook."
)


uploaded = st.file_uploader(
    "Upload populated diagnostic template (.xlsx)",
    type=["xlsx"],
)


if uploaded:
    st.success(f"Loaded file: {uploaded.name}")


run_btn = st.button(
    "Run Spend Analysis",
    type="primary",
    use_container_width=True,
)


if run_btn:
    if not uploaded:
        st.error("Please upload a workbook first.")
        st.stop()

    api_key = st.secrets.get("CLAUDE_API_KEY")

    if not api_key:
        st.error("Missing CLAUDE_API_KEY in Streamlit secrets")
        st.stop()

    supabase_url = st.secrets.get("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY")

    log_container = st.empty()

    logs = []

    def push_log(msg: str):
        logs.append(msg)
        log_container.code("
".join(logs))

    try:
        with st.spinner("Running pipeline..."):
            result = pipeline.run_pipeline(
                uploaded_workbook_bytes=uploaded.getvalue(),
                anthropic_api_key=api_key,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                status=push_log,
            )

        # Compatible with both return formats
        if len(result) == 3:
            output_bytes, filename, dashboard_data = result
        else:
            output_bytes, filename = result
            dashboard_data = {}

        st.success("Pipeline completed successfully")

        # Save dashboard payload separately
        try:
            dashboard_id = storage.save_dashboard_json(dashboard_data)

            st.success(
                f"Dashboard payload saved successfully · ID: {dashboard_id}"
            )

        except Exception as e:
            st.warning(f"Could not save dashboard payload: {e}")

        st.download_button(
            label="Download Completed Workbook",
            data=output_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.info(
            "Dashboard frontend migration is currently in progress. "
            "Backend processing has been stabilized first."
        )

    except Exception as e:
        st.error(f"Pipeline failed: {e}")

        with st.expander("Full traceback"):
            st.code(traceback.format_exc())
