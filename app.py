"""
Treya Spend Diagnostic — Streamlit UI.

Run locally:   streamlit run app.py
Deployed at:   <your-app-name>.streamlit.app
"""

import io
import time
import traceback
from datetime import datetime

import streamlit as st

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
# Optional SSO gate.
# Uncomment after configuring auth in Streamlit Cloud (see DEPLOY.md, Section 9).
# ---------------------------------------------------------------------------
# if not st.user.is_logged_in:
#     st.title("Treya Spend Diagnostic")
#     st.write("Please sign in with your Treya Google account to continue.")
#     if st.button("Sign in with Google"):
#         st.login("google")
#     st.stop()
#
# ALLOWED_DOMAIN = "treyapartners.com"
# user_email = (st.user.email or "").lower()
# if not user_email.endswith(f"@{ALLOWED_DOMAIN}"):
#     st.error(f"Access restricted to @{ALLOWED_DOMAIN} accounts.")
#     if st.button("Sign out"):
#         st.logout()
#     st.stop()


# ---------------------------------------------------------------------------
# Sidebar — settings + run info
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Treya Spend Diagnostic")
    st.caption("AP analysis & savings opportunity tool")
    st.divider()

    st.markdown("**Configuration**")
    api_status = "✅ Connected" if st.secrets.get("CLAUDE_API_KEY") else "❌ Missing"
    supa_status = "✅ Connected" if st.secrets.get("SUPABASE_URL") and st.secrets.get("SUPABASE_KEY") else "⚠️ Not configured (running without cache)"
    st.caption(f"Anthropic API: {api_status}")
    st.caption(f"Supabase cache: {supa_status}")

    st.divider()
    st.markdown("**Recent runs**")
    if "run_history" not in st.session_state:
        st.session_state.run_history = []
    if not st.session_state.run_history:
        st.caption("No runs yet in this session.")
    else:
        for entry in reversed(st.session_state.run_history[-5:]):
            st.caption(f"• {entry['time']} — {entry['company']}")


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("Treya Spend Diagnostic")
st.caption("Upload a populated Diagnostic Template, run the pipeline, download the analysis.")

# Upload step
st.markdown("### 1. Upload diagnostic template")
uploaded = st.file_uploader(
    "Drop the populated Diagnostic Template (.xlsx) here",
    type=["xlsx"],
    help="The template must contain Notes (with company/PE/industry in D3:D5), Consolidated Data, "
         "Taxonomy, and the empty tabs the pipeline populates.",
)

# Run step
st.markdown("### 2. Run analysis")
run_btn = st.button("Run pipeline", type="primary", disabled=(uploaded is None))

# Output area
if run_btn and uploaded is not None:
    api_key = st.secrets.get("CLAUDE_API_KEY")
    if not api_key:
        st.error("CLAUDE_API_KEY is not configured. See deploy guide.")
        st.stop()

    supabase_url = st.secrets.get("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY")

    log_lines: list[str] = []
    log_placeholder = st.empty()

    def push_log(msg: str):
        log_lines.append(msg)
        # Show the last ~40 lines so the log doesn't grow forever
        log_placeholder.code("\n".join(log_lines[-40:]), language="text")

    with st.status("Running pipeline…", expanded=True) as status_box:
        start = time.time()
        try:
            uploaded_bytes = uploaded.getvalue()
            output_bytes, filename = pipeline.run_pipeline(
                uploaded_workbook_bytes=uploaded_bytes,
                anthropic_api_key=api_key,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                status=push_log,
            )
            elapsed = time.time() - start
            status_box.update(label=f"✅ Completed in {elapsed:.0f}s", state="complete")

            st.success(f"Analysis complete. Total runtime: **{elapsed:.0f} seconds**")
            st.download_button(
                label=f"⬇️  Download {filename}",
                data=output_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

            # Record run
            st.session_state.run_history.append({
                "time": datetime.now().strftime("%H:%M"),
                "company": filename.split("_AP_Analysis")[0],
            })

        except KeyError as e:
            status_box.update(label="❌ Template mismatch", state="error")
            st.error(
                f"The uploaded file is missing the expected sheet/cell: **{e}**. "
                "Verify you uploaded the populated Diagnostic Template, not a custom workbook."
            )
            st.code(traceback.format_exc(), language="text")

        except Exception as e:
            status_box.update(label="❌ Pipeline failed", state="error")
            st.error(f"Unexpected error: **{type(e).__name__}: {e}**")
            with st.expander("Full traceback (share this with engineering if reporting a bug)"):
                st.code(traceback.format_exc(), language="text")

elif run_btn and uploaded is None:
    st.warning("Upload a file first.")
