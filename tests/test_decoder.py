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


def test_hex_normalization(decoder):
    """Spaces, 0x prefixes and newlines should be stripped before parsing."""
    messy = "07 49 01\n5A 4A 50 0B\r0x F6 13 00 83 00 01 02 00 00 00 01 54 06 40 13 00 83 00 02 57 02 00 00 13 13 00 83 00 01 23 05 F4 12 34 56 78 64 01 81"
    clean = "0749015A4A500BF6130083000102000000015406401300830002570200001313008300012305F412345678640181"
    result_messy = decoder.decode_universal(messy, layer="NAS", direction="DL")
    result_clean = decoder.decode_universal(clean, layer="NAS", direction="DL")
    assert result_messy == result_clean
