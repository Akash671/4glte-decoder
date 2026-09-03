import pytest

from app.decoder.rrc_nas_decoder import RRCNASDecoder


@pytest.fixture(scope="module")
def decoder():
    return RRCNASDecoder()


def test_decode_nas_tau_accept(decoder):
    hex_str = (
        "0749015A4A500BF6130083000102000000015406401300830002570200001313008300012305F412345678640181"
    )
    result = decoder.decode_universal(hex_str, layer="NAS", channel="DCCH", direction="DL")
    assert "NAS_Message" in result
    assert "error" not in result["NAS_Message"]

    # Should use the structured to_json() path, not the raw get_val() or
    # text-dump fallbacks -- i.e. real field names, not positional tuples.
    assert "nas_struct" in result["NAS_Message"]
    nas = result["NAS_Message"]["nas_struct"]
    assert "EMMTrackingAreaUpdateAccept" in nas


def test_decode_rrc_dl_dcch(decoder):
    hex_str = "5631F2857DE6"
    result = decoder.decode_universal(hex_str, layer="RRC", channel="DCCH", direction="DL")
    assert "RRC_Message" in result or "error" in result


def test_decode_rrc_ul_ccch(decoder):
    hex_str = "5DA6A5878E06"
    result = decoder.decode_universal(hex_str, layer="RRC", channel="CCCH", direction="UL")
    assert "RRC_Message" in result or "error" in result


def test_invalid_hex_string(decoder):
    # "not-hex" has an odd length, so it fails at the unhexlify step
    # before layer-specific decoding even starts.
    result = decoder.decode_universal("not-hex", layer="NAS")
    assert "error" in result

    # An even-length but non-hexadecimal string also fails cleanly.
    result2 = decoder.decode_universal("zzzz", layer="NAS")
    assert "error" in result2


def test_unknown_rrc_configuration(decoder):
    result = decoder.decode_universal("AABB", layer="RRC", channel="BOGUS", direction="UL")
    assert "error" in result


def test_unknown_layer(decoder):
    result = decoder.decode_universal("AABB", layer="XYZ")
    assert "error" in result


def test_nas_error_code_has_human_readable_meaning(decoder):
    """Malformed-but-even-length hex should hit pycrate's error 96/97/111 path,
    and we should attach a plain-English explanation, not just the bare code."""
    result = decoder.decode_universal("FFFF", layer="NAS", direction="DL")
    nas_msg = result["NAS_Message"]
    assert "error" in nas_msg
    assert "error_meaning" in nas_msg
    assert isinstance(nas_msg["error_meaning"], str)
    assert len(nas_msg["error_meaning"]) > 0


def test_rrc_decode_diagnostics_flag_partial_consumption(decoder):
    """This hex decodes 'successfully' by pycrate's rules but only consumes a
    small fraction of the buffer -- the diagnostic should flag that."""
    result = decoder.decode_universal("5631F2857DE6", layer="RRC", channel="DCCH", direction="DL")
    assert "_decode_diagnostics" in result
    diag = result["_decode_diagnostics"]
    assert diag["input_bytes"] == 6
    assert diag["bytes_consumed_on_reencode"] < diag["input_bytes"]
    assert "warning" in diag


def test_rrc_decode_diagnostics_no_warning_on_full_consumption(decoder):
    """A genuinely correct decode (RRC Connection Request) should fully
    consume its buffer and NOT trigger the partial-consumption warning."""
    result = decoder.decode_universal("5DA6A5878E06", layer="RRC", channel="CCCH", direction="UL")
    assert "_decode_diagnostics" in result
    diag = result["_decode_diagnostics"]
    assert diag["bytes_consumed_on_reencode"] == diag["input_bytes"]
    assert "warning" not in diag


def test_ue_capability_information_ul_dcch(decoder):
    """UECapabilityInformation (UE->NW, uplink) via Layer=RRC/Channel=DCCH/
    Direction=UL. Hex built with pycrate itself as ground truth: a minimal
    valid ue-CapabilityRAT-ContainerList with one EUTRA entry."""
    result = decoder.decode_universal("3801004000000000", layer="RRC", channel="DCCH", direction="UL")
    assert "RRC_Message" in result
    msg_type = result["RRC_Message"]["message"][1][0]
    assert msg_type == "ueCapabilityInformation"

    # Should fully consume the buffer -- no partial-decode warning
    assert "_decode_diagnostics" in result
    diag = result["_decode_diagnostics"]
    assert diag["bytes_consumed_on_reencode"] == diag["input_bytes"]
    assert "warning" not in diag


def test_hex_normalization(decoder):
    """Spaces, 0x prefixes and newlines should be stripped before parsing."""
    messy = "07 49 01\n5A 4A 50 0B\r0x F6 13 00 83 00 01 02 00 00 00 01 54 06 40 13 00 83 00 02 57 02 00 00 13 13 00 83 00 01 23 05 F4 12 34 56 78 64 01 81"
    clean = "0749015A4A500BF6130083000102000000015406401300830002570200001313008300012305F412345678640181"
    result_messy = decoder.decode_universal(messy, layer="NAS", direction="DL")
    result_clean = decoder.decode_universal(clean, layer="NAS", direction="DL")
    assert result_messy == result_clean
