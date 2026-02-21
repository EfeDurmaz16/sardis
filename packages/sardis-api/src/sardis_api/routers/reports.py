"""Compliance Report API routes."""
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/reports", tags=["reports"])

# Lazy init
_generator = None
def _get_generator():
    global _generator
    if _generator is None:
        from sardis_v2_core.compliance_reports import ComplianceReportGenerator
        _generator = ComplianceReportGenerator()
    return _generator

class GenerateReportRequest(BaseModel):
    report_type: str  # monthly_spending, policy_compliance, kya_verification, audit_trail, tax_report
    date_from: date
    date_to: date
    org_id: str | None = None
    agent_ids: list[str] | None = None
    format: str = "json"  # json, csv, html

class ScheduleRequest(BaseModel):
    report_type: str
    frequency: str = "monthly"
    date_from: date
    date_to: date
    email_to: list[str] = []

@router.post("/generate")
async def generate_report(req: GenerateReportRequest):
    from sardis_v2_core.compliance_reports import ReportConfig, ReportType, ReportFormat
    try:
        rt = ReportType(req.report_type)
        fmt = ReportFormat(req.format)
    except ValueError as e:
        raise HTTPException(400, f"Invalid type: {e}")
    config = ReportConfig(report_type=rt, date_from=req.date_from, date_to=req.date_to, org_id=req.org_id, agent_ids=req.agent_ids, format=fmt)
    gen = _get_generator()
    result = await gen.generate(config)
    return {"report_id": result.id, "report_type": result.report_type.value, "generated_at": result.generated_at.isoformat(), "summary": result.summary, "data": result.data}

@router.get("/{report_id}")
async def get_report(report_id: str):
    gen = _get_generator()
    result = gen.get_report(report_id)
    if not result:
        raise HTTPException(404, "Report not found")
    return {"report_id": result.id, "report_type": result.report_type.value, "generated_at": result.generated_at.isoformat(), "summary": result.summary, "data": result.data}

@router.get("")
async def list_reports(limit: int = Query(20, le=100), offset: int = Query(0, ge=0)):
    gen = _get_generator()
    reports = gen.list_reports()
    return {"reports": [{"report_id": r.id, "report_type": r.report_type.value, "generated_at": r.generated_at.isoformat(), "summary": r.summary} for r in reports[offset:offset+limit]], "total": len(reports)}

@router.get("/{report_id}/download")
async def download_report(report_id: str, format: str = Query("html")):
    from fastapi.responses import HTMLResponse, PlainTextResponse
    gen = _get_generator()
    result = gen.get_report(report_id)
    if not result:
        raise HTTPException(404, "Report not found")
    if format == "csv":
        csv_data = gen.export_csv(result)
        return PlainTextResponse(csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={report_id}.csv"})
    elif format == "html":
        html_data = gen.export_html(result)
        return HTMLResponse(html_data)
    else:
        return {"report_id": result.id, "data": result.data}

@router.post("/schedule")
async def create_schedule(req: ScheduleRequest):
    from sardis_v2_core.compliance_reports import ReportSchedule, ReportType, ReportConfig, ReportFormat
    try:
        rt = ReportType(req.report_type)
    except ValueError:
        raise HTTPException(400, "Invalid report type")
    config = ReportConfig(report_type=rt, date_from=req.date_from, date_to=req.date_to, format=ReportFormat.HTML)
    schedule = ReportSchedule(report_type=rt, frequency=req.frequency, config=config, email_to=req.email_to)
    gen = _get_generator()
    gen.create_schedule(schedule)
    return {"schedule_id": schedule.id, "report_type": rt.value, "frequency": req.frequency, "enabled": True}

@router.get("/schedules/list")
async def list_schedules():
    gen = _get_generator()
    schedules = gen.get_schedules()
    return {"schedules": [{"id": s.id, "report_type": s.report_type.value, "frequency": s.frequency, "enabled": s.enabled, "email_to": s.email_to} for s in schedules]}

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    gen = _get_generator()
    if not gen.delete_schedule(schedule_id):
        raise HTTPException(404, "Schedule not found")
    return {"deleted": True}

@router.get("/types/list")
async def list_report_types():
    return {"types": [
        {"id": "monthly_spending", "name": "Monthly Spending Report", "description": "Per-agent and per-team spending breakdown with MoM comparison"},
        {"id": "policy_compliance", "name": "Policy Compliance Report", "description": "Policy violations, blocks, compliance rate analysis"},
        {"id": "kya_verification", "name": "KYA Verification Report", "description": "Agent identity verification status and expiry tracking"},
        {"id": "audit_trail", "name": "Audit Trail Report", "description": "Tamper-evident ledger dump with hash chain verification"},
        {"id": "tax_report", "name": "Tax Report", "description": "Categorized spending for accounting with tax codes and jurisdictions"},
    ]}
