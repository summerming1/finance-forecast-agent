"""Streamlit host for the approved HTML interface. No extra HTTP/API service."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent.focused_identity import identity


def render() -> None:
    st.set_page_config(page_title="Research Workspace", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(
        """<style>
    [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display:none}
    .stMainBlockContainer {padding:0!important;max-width:none!important}
    [data-testid="stMain"] {overflow:hidden}
    .stMainBlockContainer > div {gap:0}
    iframe[title*="agent_workspace"] {display:block;border:0;width:100%}
    </style>""",
        unsafe_allow_html=True,
    )
    state = Path(os.getenv("FFA_WORKSPACE_STATE_DB", "projects/workspace/runtime.sqlite3")).resolve()
    tenant = os.getenv("FFA_WORKSPACE_TENANT", "default")
    service = WorkspaceUI(
        state, tenant_id=tenant, default_project=os.getenv("FFA_WORKSPACE_PROJECT_DIR", "projects/finance_agent")
    )
    scope = identity({"state": str(state), "tenant": tenant}, domain="workspace-ui-session-v1")
    key = "agent_workspace_state:" + scope
    if key not in st.session_state:
        st.session_state[key] = {
            "project_id": st.query_params.get("project", ""),
            "campaign_id": st.query_params.get("campaign", ""),
            "candidate_id": st.query_params.get("candidate", ""),
            "seen": [],
            "response": None,
        }
    ui = st.session_state[key]
    try:
        snapshot = service.snapshot(ui["project_id"], ui["campaign_id"], ui["candidate_id"])
    except Exception as exc:  # noqa: BLE001 -- UI boundary must report backend failures without executing fallbacks
        snapshot = service.snapshot()
        snapshot["errors"].append(_error_message(exc))
    if snapshot["current"]:
        ui["candidate_id"] = snapshot["current"]["selected_candidate_id"]
    component = components.declare_component("agent_workspace", path=str(Path(__file__).parent / "workspace_frontend"))
    event = component(
        snapshot=snapshot, response=ui["response"], scope_id=scope, key="agent-workspace:" + scope, default=None
    )
    if not isinstance(event, dict) or event.get("id") in ui["seen"]:
        return
    eid = event.get("id")
    if not isinstance(eid, str) or not eid or len(eid) > 100:
        return
    ui["seen"] = (ui["seen"] + [eid])[-256:]
    try:
        name, args = event.get("action"), event.get("args", {})
        if not isinstance(args, dict):
            raise TypeError("Invalid action arguments")
        if name == "refresh":
            result = {}
        elif name == "select":
            pid, cid, candidate = args.get("project_id", ""), args.get("campaign_id", ""), args.get("candidate_id", "")
            service.snapshot(pid, cid, candidate)  # server re-resolves identities; no dispatch
            ui.update(project_id=pid, campaign_id=cid, candidate_id=candidate)
            st.query_params.from_dict(
                {k: v for k, v in [("project", pid), ("campaign", cid), ("candidate", candidate)] if v}
            )
            result = {}
        elif name == "navigate_legacy":
            # Only these static destinations are allowed; never follow browser supplied URLs.
            target = args.get("target")
            if target not in {"lab", "legacy"}:
                raise ValueError("Unknown legacy destination")
            st.query_params.from_dict({target: "1"})
            st.session_state.pop(key, None)
            st.rerun()
        else:
            result = service.execute(name, args, eid)
            if name in {"create", "continue"}:
                ui.update(project_id=result["project_id"], campaign_id=result["campaign_id"], candidate_id="")
                st.query_params.from_dict({"project": result["project_id"], "campaign": result["campaign_id"]})
            elif name == "register_project":
                ui.update(project_id=result["project_id"], campaign_id="", candidate_id="")
                st.query_params.from_dict({"project": result["project_id"]})
        ui["response"] = {"id": eid, "ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001 -- UI boundary must report backend failures without executing fallbacks
        ui["response"] = {"id": eid, "ok": False, "error": _error_message(exc), "error_type": type(exc).__name__}
    st.rerun()


def _error_message(exc: Exception) -> str:
    text = str(exc)[:2000]
    for key in ("OPENAI_API_KEY", "DASHSCOPE_API_KEY", "TEACHER_API_KEY"):
        value = os.getenv(key)
        if value:
            text = text.replace(value, "[redacted]")
    return text or type(exc).__name__


if __name__ == "__main__":
    render()
