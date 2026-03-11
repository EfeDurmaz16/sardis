"""ERC-8021: Transaction Attribution via calldata suffix.

Appends attribution codes to EVM transaction calldata for off-chain
analytics and revenue sharing. Smart contracts ignore the suffix;
indexers parse it backward from the calldata end.

Spec: https://www.erc8021.com/
Reference: https://github.com/base/builder-codes

Format (from end):
    [original calldata] + [codes] + [codesLength: 1B] + [schemaId: 1B] + [marker: 16B]

Marker: 0x80218021802180218021802180218021 ("8021" × 4 in hex)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ERC-8021 marker: "8021" repeated to fill 16 bytes
ERC8021_MARKER = bytes.fromhex("80218021802180218021802180218021")
MARKER_LENGTH = 16
SCHEMA_LENGTH = 1
CODES_LENGTH_FIELD = 1

# Default Schema ID
SCHEMA_V0 = 0x00

# Sardis attribution code
SARDIS_CODE = "sardis"

# Valid code characters: lowercase alphanumeric + underscore
_VALID_CODE_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_")


@dataclass
class AttributionData:
    """Parsed attribution data from a transaction."""
    codes: list[str]
    schema_id: int = SCHEMA_V0
    raw_suffix: bytes = b""

    @property
    def primary_code(self) -> str | None:
        """First attribution code (primary builder)."""
        return self.codes[0] if self.codes else None


def validate_code(code: str) -> bool:
    """Validate an attribution code.

    Valid codes: 1-32 chars, lowercase alphanumeric + underscore only.
    """
    if not code or len(code) > 32:
        return False
    return all(c in _VALID_CODE_CHARS for c in code)


def encode_attribution(
    codes: list[str] | str,
    schema_id: int = SCHEMA_V0,
) -> bytes:
    """Encode attribution codes into an ERC-8021 calldata suffix.

    Args:
        codes: Single code string or list of codes to attribute.
        schema_id: Schema version (default: 0).

    Returns:
        Bytes to append to transaction calldata.

    Raises:
        ValueError: If any code is invalid.
    """
    if isinstance(codes, str):
        codes = [codes]

    for code in codes:
        if not validate_code(code):
            raise ValueError(
                f"Invalid attribution code '{code}': "
                f"must be 1-32 chars, lowercase alphanumeric + underscore"
            )

    # Join codes with comma separator (0x2C)
    codes_str = ",".join(codes)
    codes_bytes = codes_str.encode("ascii")

    if len(codes_bytes) > 255:
        raise ValueError(
            f"Combined codes length {len(codes_bytes)} exceeds maximum 255 bytes"
        )

    # Build suffix: codes + codesLength + schemaId + marker
    suffix = (
        codes_bytes
        + bytes([len(codes_bytes)])
        + bytes([schema_id])
        + ERC8021_MARKER
    )

    return suffix


def append_attribution(
    calldata: bytes,
    codes: list[str] | str,
    schema_id: int = SCHEMA_V0,
) -> bytes:
    """Append ERC-8021 attribution suffix to transaction calldata.

    Args:
        calldata: Original transaction calldata.
        codes: Attribution code(s) to append.
        schema_id: Schema version.

    Returns:
        Calldata with attribution suffix appended.
    """
    suffix = encode_attribution(codes, schema_id)
    return calldata + suffix


def decode_attribution(calldata: bytes) -> AttributionData | None:
    """Decode ERC-8021 attribution from transaction calldata.

    Parses backward from the end of calldata looking for the ERC-8021
    marker. Returns None if no valid attribution is found.

    Args:
        calldata: Full transaction calldata (with potential suffix).

    Returns:
        AttributionData with parsed codes, or None.
    """
    min_length = MARKER_LENGTH + SCHEMA_LENGTH + CODES_LENGTH_FIELD + 1  # At least 1 byte code
    if len(calldata) < min_length:
        return None

    # Check for marker at the end
    marker = calldata[-MARKER_LENGTH:]
    if marker != ERC8021_MARKER:
        return None

    # Extract schema ID
    schema_id = calldata[-(MARKER_LENGTH + SCHEMA_LENGTH)]

    # Extract codes length
    codes_length = calldata[-(MARKER_LENGTH + SCHEMA_LENGTH + CODES_LENGTH_FIELD)]

    if codes_length == 0:
        return AttributionData(codes=[], schema_id=schema_id)

    # Extract codes bytes
    suffix_total = MARKER_LENGTH + SCHEMA_LENGTH + CODES_LENGTH_FIELD + codes_length
    if len(calldata) < suffix_total:
        logger.warning("Calldata too short for declared codes length %d", codes_length)
        return None

    codes_start = -(MARKER_LENGTH + SCHEMA_LENGTH + CODES_LENGTH_FIELD + codes_length)
    codes_end = -(MARKER_LENGTH + SCHEMA_LENGTH + CODES_LENGTH_FIELD)
    codes_bytes = calldata[codes_start:codes_end]

    try:
        codes_str = codes_bytes.decode("ascii")
    except UnicodeDecodeError:
        logger.warning("Non-ASCII bytes in attribution codes")
        return None

    codes = [c for c in codes_str.split(",") if c]

    return AttributionData(
        codes=codes,
        schema_id=schema_id,
        raw_suffix=calldata[-suffix_total:],
    )


def strip_attribution(calldata: bytes) -> bytes:
    """Remove ERC-8021 attribution suffix from calldata if present.

    Returns the original calldata without the attribution suffix.
    """
    attribution = decode_attribution(calldata)
    if attribution is None:
        return calldata

    suffix_len = len(attribution.raw_suffix)
    return calldata[:-suffix_len]


def has_attribution(calldata: bytes) -> bool:
    """Check if calldata contains an ERC-8021 attribution suffix."""
    if len(calldata) < MARKER_LENGTH:
        return False
    return calldata[-MARKER_LENGTH:] == ERC8021_MARKER


def sardis_attribution(extra_codes: list[str] | None = None) -> bytes:
    """Generate Sardis-branded attribution suffix.

    Always includes "sardis" as the primary code, optionally followed
    by additional codes (e.g. partner/integration identifiers).

    Args:
        extra_codes: Additional attribution codes after "sardis".

    Returns:
        ERC-8021 suffix bytes.
    """
    codes = [SARDIS_CODE]
    if extra_codes:
        codes.extend(extra_codes)
    return encode_attribution(codes)
