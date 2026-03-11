"""Tests for ERC-8021 Transaction Attribution.

Covers issue #129.
"""
from __future__ import annotations

import pytest

from sardis_protocol.erc8021 import (
    ERC8021_MARKER,
    SARDIS_CODE,
    AttributionData,
    append_attribution,
    decode_attribution,
    encode_attribution,
    has_attribution,
    sardis_attribution,
    strip_attribution,
    validate_code,
)


class TestCodeValidation:
    """Test attribution code validation."""

    def test_valid_codes(self):
        assert validate_code("sardis") is True
        assert validate_code("baseapp") is True
        assert validate_code("my_app_123") is True
        assert validate_code("a") is True

    def test_invalid_codes(self):
        assert validate_code("") is False
        assert validate_code("A" * 33) is False  # Too long
        assert validate_code("UPPER") is False
        assert validate_code("has space") is False
        assert validate_code("has-dash") is False
        assert validate_code("has.dot") is False


class TestEncodeAttribution:
    """Test encoding attribution codes into calldata suffix."""

    def test_single_code(self):
        suffix = encode_attribution("sardis")
        # Should end with marker
        assert suffix[-16:] == ERC8021_MARKER
        # Schema ID should be 0
        assert suffix[-17] == 0x00
        # Codes length
        assert suffix[-18] == len("sardis")
        # Codes
        assert suffix[:len("sardis")] == b"sardis"

    def test_multiple_codes(self):
        suffix = encode_attribution(["sardis", "partner_app"])
        assert suffix[-16:] == ERC8021_MARKER
        codes_str = "sardis,partner_app"
        assert suffix[-18] == len(codes_str)
        assert suffix[:len(codes_str)] == codes_str.encode("ascii")

    def test_invalid_code_raises(self):
        with pytest.raises(ValueError, match="Invalid attribution code"):
            encode_attribution("INVALID")

    def test_codes_too_long_raises(self):
        # Create codes that exceed 255 bytes total
        codes = [f"code_{i:03d}" for i in range(50)]
        with pytest.raises(ValueError, match="exceeds maximum 255 bytes"):
            encode_attribution(codes)


class TestDecodeAttribution:
    """Test decoding attribution from calldata."""

    def test_decode_single_code(self):
        original = bytes.fromhex("a9059cbb")  # ERC-20 transfer selector
        tagged = append_attribution(original, "sardis")

        result = decode_attribution(tagged)
        assert result is not None
        assert result.codes == ["sardis"]
        assert result.primary_code == "sardis"
        assert result.schema_id == 0

    def test_decode_multiple_codes(self):
        original = bytes.fromhex("a9059cbb")
        tagged = append_attribution(original, ["sardis", "helicone", "agent_xyz"])

        result = decode_attribution(tagged)
        assert result is not None
        assert result.codes == ["sardis", "helicone", "agent_xyz"]
        assert result.primary_code == "sardis"

    def test_decode_no_attribution(self):
        plain_calldata = bytes.fromhex("a9059cbb0000000000000000")
        result = decode_attribution(plain_calldata)
        assert result is None

    def test_decode_too_short(self):
        result = decode_attribution(b"\x00" * 5)
        assert result is None

    def test_roundtrip(self):
        """Encode → append → decode should recover original codes."""
        original = bytes(100)  # 100 zero bytes
        codes = ["sardis", "partner"]
        tagged = append_attribution(original, codes)

        result = decode_attribution(tagged)
        assert result is not None
        assert result.codes == codes


class TestStripAttribution:
    """Test removing attribution suffix."""

    def test_strip_existing(self):
        original = bytes.fromhex("a9059cbb")
        tagged = append_attribution(original, "sardis")

        stripped = strip_attribution(tagged)
        assert stripped == original

    def test_strip_no_attribution(self):
        original = bytes.fromhex("a9059cbb")
        stripped = strip_attribution(original)
        assert stripped == original


class TestHasAttribution:
    """Test attribution detection."""

    def test_has_attribution_true(self):
        tagged = append_attribution(b"\x00", "sardis")
        assert has_attribution(tagged) is True

    def test_has_attribution_false(self):
        assert has_attribution(b"\x00" * 20) is False

    def test_has_attribution_short(self):
        assert has_attribution(b"\x00") is False


class TestSardisAttribution:
    """Test Sardis-specific attribution helper."""

    def test_sardis_only(self):
        suffix = sardis_attribution()
        result = decode_attribution(b"\x00" + suffix)
        assert result is not None
        assert result.codes == ["sardis"]

    def test_sardis_with_extras(self):
        suffix = sardis_attribution(extra_codes=["helicone", "crewai"])
        result = decode_attribution(b"\x00" + suffix)
        assert result is not None
        assert result.codes == ["sardis", "helicone", "crewai"]


class TestModuleExports:
    """Verify exports from sardis_protocol."""

    def test_attribution_data_exported(self):
        from sardis_protocol import AttributionData
        assert AttributionData is not None

    def test_encode_exported(self):
        from sardis_protocol import encode_attribution
        assert encode_attribution is not None

    def test_decode_exported(self):
        from sardis_protocol import decode_attribution
        assert decode_attribution is not None
