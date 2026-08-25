"""
Pydantic models for the LTE RRC/NAS decoder API.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class Layer(str, Enum):
    RRC = "RRC"
    NAS = "NAS"


class Channel(str, Enum):
    BCH = "BCH"
    PBCH = "PBCH"
    BCCH = "BCCH"
    PCCH = "PCCH"
    CCCH = "CCCH"
    DCCH = "DCCH"
    DL_SCH = "DL-SCH"
    PDSCH = "PDSCH"
    UE_EUTRA_CAPABILITY = "UE-EUTRA-CAPABILITY"


class Direction(str, Enum):
    UL = "UL"
    DL = "DL"


class DecodeRequest(BaseModel):
    """Input payload for a single hex message decode."""

    hex_str: str = Field(
        ...,
        min_length=2,
        description="Raw hex string of the captured message (spaces / 0x prefix / newlines are stripped automatically).",
        examples=["0749015A4A500BF6130083000102000000015406401300830002570200001313008300012305F412345678640181"],
    )
    layer: Layer = Field(default=Layer.RRC, description="Protocol layer to decode: RRC or NAS.")
    channel: Channel = Field(default=Channel.DCCH, description="Logical channel the message was captured on. Ignored when layer=NAS.")
    direction: Direction = Field(default=Direction.UL, description="Link direction: UL (uplink) or DL (downlink).")

    @field_validator("hex_str")
    @classmethod
    def validate_hex(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("0x", "").replace("\n", "").replace("\r", "")
        if len(cleaned) % 2 != 0:
            raise ValueError("Hex string must have an even number of digits.")
        try:
            int(cleaned, 16)
        except ValueError as exc:
            raise ValueError("hex_str is not valid hexadecimal.") from exc
        return v


class DecodeResponse(BaseModel):
    """Structured decode result returned to the client."""

    ok: bool = Field(..., description="False if decoding raised an error.")
    layer: Layer
    channel: Channel
    direction: Direction
    result: Any = Field(..., description="Decoded message tree (or {'error': ...} on failure).")
    error: Optional[str] = Field(default=None, description="Top-level error message, if any.")


class HealthResponse(BaseModel):
    status: str = "ok"
