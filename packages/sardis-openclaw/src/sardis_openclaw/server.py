"""OpenClaw-compatible skill server with discovery and execution endpoints."""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sardis_openclaw import SKILL_REGISTRY, get_executable_skill
from sardis_openclaw.base import SkillContext

app = FastAPI(
    title="Sardis OpenClaw Skill Server",
    version="1.0.0",
    description="Payment OS for AI Agents - OpenClaw skill server exposing wallet, payment, policy, and compliance capabilities.",
)


class SkillInfo(BaseModel):
    name: str
    description: str
    parameters: list[str]
    required_permissions: list[str]


class ExecuteRequest(BaseModel):
    params: dict[str, Any]
    context: dict[str, str]


class ExecuteResponse(BaseModel):
    success: bool
    data: dict[str, Any] = {}
    error: str | None = None


# ---------------------------------------------------------------------------
# Health / metadata
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check for monitoring."""
    return {"status": "ok", "service": "sardis-openclaw", "skills": len(SKILL_REGISTRY)}


@app.get("/")
async def root():
    """Root metadata endpoint."""
    return {
        "service": "sardis-openclaw",
        "version": "1.0.0",
        "description": "Payment OS for AI Agents",
        "skills_count": len(SKILL_REGISTRY),
        "docs": "/docs",
    }


# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------

@app.get("/skills", response_model=list[SkillInfo])
async def list_skills():
    """Discover available skills."""
    result = []
    for _name, cls in SKILL_REGISTRY.items():
        instance = cls()
        result.append(SkillInfo(
            name=instance.name,
            description=instance.description,
            parameters=instance.parameters,
            required_permissions=instance.required_permissions,
        ))
    return result


@app.get("/skills/{skill_name}", response_model=SkillInfo)
async def get_skill_info(skill_name: str):
    """Get info about a specific skill."""
    if skill_name not in SKILL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")
    instance = get_executable_skill(skill_name)
    return SkillInfo(
        name=instance.name,
        description=instance.description,
        parameters=instance.parameters,
        required_permissions=instance.required_permissions,
    )


# ---------------------------------------------------------------------------
# Skill execution
# ---------------------------------------------------------------------------

@app.post("/skills/{skill_name}/execute", response_model=ExecuteResponse)
async def execute_skill(skill_name: str, request: ExecuteRequest):
    """Execute a skill."""
    if skill_name not in SKILL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}")

    # Validate context
    required_ctx = ["api_key", "agent_id"]
    missing = [k for k in required_ctx if k not in request.context]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing context fields: {', '.join(missing)}")

    context = SkillContext(
        api_key=request.context["api_key"],
        wallet_id=request.context.get("wallet_id", ""),
        agent_id=request.context["agent_id"],
        base_url=request.context.get("base_url", os.getenv("SARDIS_API_URL", "https://api.sardis.sh/v2")),
    )

    skill = get_executable_skill(skill_name)

    # Validate parameters
    validation_err = skill.validate_params(request.params)
    if validation_err:
        raise HTTPException(status_code=422, detail=validation_err)

    result = await skill.execute(request.params, context)
    return ExecuteResponse(success=result.success, data=result.data, error=result.error)
