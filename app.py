"""
Treya Spend Diagnostic — Streamlit UI.
Updated to render an embedded dashboard after the pipeline runs.

Run locally:   streamlit run app.py
Deployed at:   <your-app-name>.streamlit.app
"""

import io
import json
import time
import traceback
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import pipeline

# ---------------------------------------------------------------------------
# Page config + theme
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Treya Spend Diagnostic",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Optional SSO gate — see DEPLOY.md Step 7 to enable.
# ---------------------------------------------------------------------------
# if not st.user.is_logged_in:
#     st.title("Treya Spend Diagnostic")
#     if st.button("Sign in with Google"):
#         st.login("google")
#     st.stop()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Treya Spend Diagnostic")
    st.caption("AP analysis & savings opportunity tool")
    st.divider()
    st.markdown("**Configuration**")
    api_status = "✅ Connected" if st.secrets.get("CLAUDE_API_KEY") else "❌ Missing"
    supa_status = ("✅ Connected" if st.secrets.get("SUPABASE_URL") and st.secrets.get("SUPABASE_KEY")
                   else "⚠️ Not configured (no cache)")
    st.caption(f"Anthropic API: {api_status}")
    st.caption(f"Supabase cache: {supa_status}")


# ---------------------------------------------------------------------------
# Session state — keep last-run data across reruns
# ---------------------------------------------------------------------------
if "last_output_bytes" not in st.session_state:
    st.session_state.last_output_bytes = None
if "last_filename" not in st.session_state:
    st.session_state.last_filename = None
if "last_dashboard_data" not in st.session_state:
    st.session_state.last_dashboard_data = None


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("Treya Spend Diagnostic")
st.caption("Upload a populated Diagnostic Template, run the pipeline, view the dashboard, and download the report.")

st.markdown("### 1. Upload diagnostic template")
uploaded = st.file_uploader(
    "Drop the populated Diagnostic Template (.xlsx) here",
    type=["xlsx"],
)

st.markdown("### 2. Run analysis")
run_btn = st.button("Run pipeline", type="primary", disabled=(uploaded is None))


# ---------------------------------------------------------------------------
# Run the pipeline
# ---------------------------------------------------------------------------
if run_btn and uploaded is not None:
    api_key = st.secrets.get("CLAUDE_API_KEY")
    if not api_key:
        st.error("CLAUDE_API_KEY is not configured.")
        st.stop()

    supabase_url = st.secrets.get("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY")

    log_lines: list[str] = []
    log_placeholder = st.empty()

    def push_log(msg: str):
        log_lines.append(msg)
        log_placeholder.code("\n".join(log_lines[-40:]), language="text")

    with st.status("Running pipeline…", expanded=True) as status_box:
        start = time.time()
        try:
            output_bytes, filename, dashboard_data = pipeline.run_pipeline(
                uploaded_workbook_bytes=uploaded.getvalue(),
                anthropic_api_key=api_key,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                status=push_log,
            )
            elapsed = time.time() - start
            status_box.update(label=f"✅ Completed in {elapsed:.0f}s", state="complete")

            # Persist into session so the dashboard survives subsequent reruns
            st.session_state.last_output_bytes = output_bytes
            st.session_state.last_filename = filename
            st.session_state.last_dashboard_data = dashboard_data

        except KeyError as e:
            status_box.update(label="❌ Template mismatch", state="error")
            st.error(f"Missing expected sheet/cell in template: **{e}**.")
            st.code(traceback.format_exc(), language="text")
            st.stop()
        except Exception as e:
            status_box.update(label="❌ Pipeline failed", state="error")
            st.error(f"Unexpected error: **{type(e).__name__}: {e}**")
            with st.expander("Full traceback"):
                st.code(traceback.format_exc(), language="text")
            st.stop()

elif run_btn and uploaded is None:
    st.warning("Upload a file first.")


# ---------------------------------------------------------------------------
# Render results — survives reruns because everything is in session_state
# ---------------------------------------------------------------------------
if st.session_state.last_dashboard_data is not None:
    st.success(f"Analysis ready for **{st.session_state.last_dashboard_data['client']}**")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.download_button(
            label="⬇️  Download Excel report",
            data=st.session_state.last_output_bytes,
            file_name=st.session_state.last_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    st.divider()
    st.markdown("### 3. Analysis Dashboard")

    # Read template, inject data, embed
    dashboard_template = Path(__file__).parent / "dashboard.html"
    html_content = dashboard_template.read_text(encoding="utf-8")
    injected_data = json.dumps(st.session_state.last_dashboard_data)
    final_html = html_content.replace("__DATA__", injected_data)

    components.html(final_html, height=2400, scrolling=True)
