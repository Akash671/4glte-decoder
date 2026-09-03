"""
Streamlit GUI for the LTE RRC/NAS decoder.

Run locally:
    streamlit run app/streamlit_app.py

Set DECODER_MODE=api and API_URL to point at a running FastAPI instance
instead of decoding in-process (useful once you split the two deployments).
"""

import json
import os
import sys
from pathlib import Path

# Ensure the project root (parent of this app/ folder) is on sys.path.
# Streamlit executes this script directly, which only adds app/'s own
# directory to sys.path -- not the project root -- so "from app..."
# imports fail unless we add it ourselves, regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import streamlit as st

from app import analytics
from app.decoder.rrc_nas_decoder import RRCNASDecoder

st.set_page_config(page_title="4G LTE RRC/NAS Decoder", page_icon="📡", layout="wide")

DECODER_MODE = os.getenv("DECODER_MODE", "local")  # "local" or "api"
API_URL = os.getenv("API_URL", "http://localhost:8000")

CHANNELS = ["BCH", "PBCH", "BCCH", "PCCH", "CCCH", "DCCH", "DL-SCH", "PDSCH", "UE-EUTRA-CAPABILITY"]

EXAMPLES = {
    "Tracking Area Update Accept (NAS, DL)": {
        "hex": "0749015A4A500BF6130083000102000000015406401300830002570200001313008300012305F412345678640181",
        "layer": "NAS",
        "channel": "DCCH",
        "direction": "DL",
    },
    "DL Information Transfer (RRC, DL/DCCH)": {
        "hex": "5631F2857DE6",
        "layer": "RRC",
        "channel": "DCCH",
        "direction": "DL",
    },
    "RRC Connection Request (RRC, UL/CCCH)": {
        "hex": "5DA6A5878E06",
        "layer": "RRC",
        "channel": "CCCH",
        "direction": "UL",
    },
}


@st.cache_resource
def get_local_decoder() -> RRCNASDecoder:
    return RRCNASDecoder()


def decode_local(hex_str: str, layer: str, channel: str, direction: str) -> dict:
    decoder = get_local_decoder()
    result = decoder.decode_universal(hex_str, layer=layer, channel=channel, direction=direction)
    return _json_safe(result)


def decode_via_api(hex_str: str, layer: str, channel: str, direction: str) -> dict:
    resp = requests.post(
        f"{API_URL}/decode",
        json={"hex_str": hex_str, "layer": layer, "channel": channel, "direction": direction},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _json_safe(value):
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, dict):
        return {str(_json_safe(k)): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


# ---------------------------------------------------------------- UI

st.title("📡 4G LTE RRC/NAS Decoder")
st.caption("Decode raw LTE RRC and NAS hex captures into structured, readable JSON — powered by pycrate.")

# Count each browser session as one page view, exactly once -- st.session_state
# persists across reruns within a session (every widget interaction reruns
# the whole script), but resets on a fresh tab/reload, which is what we want.
if "view_recorded" not in st.session_state:
    analytics.record_event("page_view")
    st.session_state["view_recorded"] = True

with st.sidebar:
    st.header("Settings")
    st.write(f"Decode mode: **{DECODER_MODE}**")
    if DECODER_MODE == "api":
        st.write(f"API URL: `{API_URL}`")
    st.divider()
    st.subheader("Load an example")
    choice = st.selectbox("Example messages", ["— none —"] + list(EXAMPLES.keys()))

    st.divider()
    st.subheader("📊 Usage stats")
    try:
        s = analytics.get_stats()
        c1, c2 = st.columns(2)
        c1.metric("Page views", s["total_views"])
        c2.metric("Decodes", s["total_decodes"])
        if s["success_rate"] is not None:
            st.caption(f"Success rate: {s['success_rate'] * 100:.0f}%  "
                       f"({s['success_count']} ok / {s['error_count']} error)")
        if s["decodes_by_layer"]:
            st.caption("By layer: " + ", ".join(f"{k}={v}" for k, v in s["decodes_by_layer"].items()))
        if st.button("Refresh stats", use_container_width=True):
            st.rerun()
    except Exception as exc:
        st.caption(f"Stats unavailable: {exc}")

    st.divider()
    st.subheader("👤 About the developer")
    st.markdown(
        """
        **Akash Kumar**
        AI Engineer

        [🔗 GitHub](https://github.com/Akash671)
        """
    )

default_hex, default_layer, default_channel, default_direction = "", "NAS", "DCCH", "DL"
if choice != "— none —":
    ex = EXAMPLES[choice]
    default_hex, default_layer, default_channel, default_direction = (
        ex["hex"], ex["layer"], ex["channel"], ex["direction"]
    )

col1, col2 = st.columns([2, 1])

with col1:
    hex_str = st.text_area(
        "Hex payload",
        value=default_hex,
        height=120,
        placeholder="e.g. 0749015A4A500BF6130083000102...",
    )

with col2:
    layer = st.radio("Layer", ["RRC", "NAS"], index=0 if default_layer == "RRC" else 1)
    channel = st.selectbox("Channel", CHANNELS, index=CHANNELS.index(default_channel), disabled=(layer == "NAS"))
    direction = st.radio("Direction", ["UL", "DL"], index=0 if default_direction == "UL" else 1)

decode_clicked = st.button("Decode", type="primary", use_container_width=False)

if decode_clicked:
    if not hex_str.strip():
        st.error("Please provide a hex string to decode.")
    else:
        with st.spinner("Decoding..."):
            try:
                if DECODER_MODE == "api":
                    output = decode_via_api(hex_str, layer, channel, direction)
                else:
                    output = decode_local(hex_str, layer, channel, direction)
            except Exception as exc:
                st.error(f"Decode failed: {exc}")
                output = None

        if output is not None:
            result_payload = output.get("result", output)
            has_error = isinstance(result_payload, dict) and "error" in result_payload and len(result_payload) == 1
            analytics.record_event("gui_decode", layer=layer, success=not has_error)

            if has_error:
                st.error(result_payload["error"])
            else:
                st.success("Decoded successfully.")
                st.json(result_payload)
                st.download_button(
                    "Download JSON",
                    data=json.dumps(result_payload, indent=2),
                    file_name="decoded_message.json",
                    mime="application/json",
                )
