"""Merchant Category Code (MCC) lookup service."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Load MCC data from embedded JSON
_MCC_DATA_PATH = Path(__file__).parent / "data" / "mcc_codes.json"
_MCC_DATA: Optional[dict] = None


@dataclass
class MCCInfo:
    """Information about a Merchant Category Code."""

    code: str
    description: str
    category: str
    risk_level: str  # 'low', 'medium', 'high'
    default_blocked: bool


def _load_mcc_data() -> dict:
    """Load MCC data from JSON file (cached)."""
    global _MCC_DATA
    if _MCC_DATA is None:
        with open(_MCC_DATA_PATH) as f:
            _MCC_DATA = json.load(f)
    return _MCC_DATA


def get_mcc_info(mcc_code: str) -> Optional[MCCInfo]:
    """
    Look up MCC code information.

    Args:
        mcc_code: 4-digit MCC code as string

    Returns:
        MCCInfo if code exists, None otherwise
    """
    data = _load_mcc_data()
    code_info = data["codes"].get(mcc_code)
    if not code_info:
        return None
    return MCCInfo(
        code=mcc_code,
        description=code_info["description"],
        category=code_info["category"],
        risk_level=code_info["risk_level"],
        default_blocked=code_info["default_blocked"],
    )


def get_category_codes(category: str) -> list[str]:
    """
    Get all MCC codes in a category.

    Args:
        category: Category name (e.g., 'gambling', 'healthcare')

    Returns:
        List of MCC codes in that category
    """
    data = _load_mcc_data()
    cat_info = data["categories"].get(category)
    return cat_info["codes"] if cat_info else []


def get_category_info(category: str) -> Optional[dict]:
    """
    Get category metadata.

    Args:
        category: Category name

    Returns:
        Dict with 'name', 'codes', 'default_policy' or None
    """
    data = _load_mcc_data()
    return data["categories"].get(category)


def is_blocked_category(mcc_code: str, blocked_categories: list[str]) -> bool:
    """
    Check if MCC code belongs to a blocked category.

    Args:
        mcc_code: 4-digit MCC code
        blocked_categories: List of category names to block

    Returns:
        True if MCC belongs to blocked category, False otherwise
    """
    info = get_mcc_info(mcc_code)
    if not info:
        return False  # Unknown codes allowed by default
    return info.category in blocked_categories


def get_all_categories() -> list[str]:
    """
    Get list of all available categories.

    Returns:
        List of category names
    """
    data = _load_mcc_data()
    return list(data["categories"].keys())


def get_high_risk_codes() -> list[str]:
    """
    Get all MCC codes marked as high risk.

    Returns:
        List of high-risk MCC codes
    """
    data = _load_mcc_data()
    return [
        code
        for code, info in data["codes"].items()
        if info.get("risk_level") == "high"
    ]


def get_default_blocked_codes() -> list[str]:
    """
    Get all MCC codes that are blocked by default.

    Returns:
        List of MCC codes blocked by default
    """
    data = _load_mcc_data()
    return [
        code
        for code, info in data["codes"].items()
        if info.get("default_blocked", False)
    ]


def search_mcc_by_description(query: str) -> list[MCCInfo]:
    """
    Search MCC codes by description keyword.

    Args:
        query: Search term (case-insensitive)

    Returns:
        List of matching MCCInfo objects
    """
    data = _load_mcc_data()
    query_lower = query.lower()
    results = []

    for code, info in data["codes"].items():
        if query_lower in info["description"].lower():
            results.append(
                MCCInfo(
                    code=code,
                    description=info["description"],
                    category=info["category"],
                    risk_level=info["risk_level"],
                    default_blocked=info["default_blocked"],
                )
            )

    return results


def get_mcc_data_version() -> str:
    """
    Get the version of the MCC data.

    Returns:
        Version string (e.g., '2024.1')
    """
    data = _load_mcc_data()
    return data.get("version", "unknown")
