"""Base model for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SardisModel(BaseModel):
    """Base model with common configuration."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="ignore",
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return self.model_dump(mode="json", exclude_none=True)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SardisModel":
        """Create model from dictionary."""
        return cls.model_validate(data)
