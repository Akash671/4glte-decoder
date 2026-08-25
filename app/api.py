"""
FastAPI service around RRCNASDecoder.

Run locally:
    uvicorn app.api:app --reload

Docs:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.decoder.rrc_nas_decoder import RRCNASDecoder
from app.schemas import DecodeRequest, DecodeResponse, HealthResponse

app = FastAPI(
    title="4G LTE RRC/NAS Decoder API",
    description="Decode LTE RRC and NAS hex captures into structured JSON.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

decoder = RRCNASDecoder()


def _make_json_safe(value):
    """Recursively convert bytes -> hex strings so the result is JSON serializable."""
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, dict):
        return {str(_make_json_safe(k)): _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(v) for v in value]
    return value


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/decode", response_model=DecodeResponse, tags=["decode"])
def decode(req: DecodeRequest) -> DecodeResponse:
    try:
        raw_result = decoder.decode_universal(
            hex_str=req.hex_str,
            layer=req.layer.value,
            channel=req.channel.value,
            direction=req.direction.value,
        )
    except Exception as exc:  # pragma: no cover - defensive catch-all
        raise HTTPException(status_code=500, detail=f"Unexpected decoder failure: {exc}") from exc

    safe_result = _make_json_safe(raw_result)
    has_error = isinstance(safe_result, dict) and "error" in safe_result

    return DecodeResponse(
        ok=not has_error,
        layer=req.layer,
        channel=req.channel,
        direction=req.direction,
        result=safe_result,
        error=safe_result.get("error") if has_error else None,
    )
