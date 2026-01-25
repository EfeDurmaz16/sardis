"""
Compliance report generation module.

Generates comprehensive compliance reports in PDF and JSON formats:
- Executive summary reports
- Detailed audit trail reports
- Risk assessment reports
- Regulatory filing reports (SAR, CTR)
"""
from __future__ import annotations

import io
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Types of compliance reports."""
    EXECUTIVE_SUMMARY = "executive_summary"
    AUDIT_TRAIL = "audit_trail"
    RISK_ASSESSMENT = "risk_assessment"
    TRANSACTION_MONITORING = "transaction_monitoring"
    SAR = "sar"  # Suspicious Activity Report
    CTR = "ctr"  # Currency Transaction Report
    PEP_SCREENING = "pep_screening"
    SANCTIONS_SCREENING = "sanctions_screening"
    PERIODIC_REVIEW = "periodic_review"


class ReportFormat(str, Enum):
    """Output formats for reports."""
    PDF = "pdf"
    JSON = "json"
    HTML = "html"
    CSV = "csv"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportMetadata:
    """Metadata for a generated report."""
    report_id: str
    report_type: ReportType
    format: ReportFormat
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    generated_by: str = "system"
    status: ReportStatus = ReportStatus.PENDING
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "format": self.format.value,
            "created_at": self.created_at.isoformat(),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "generated_by": self.generated_by,
            "status": self.status.value,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "error_message": self.error_message,
        }


@dataclass
class ReportSection:
    """A section within a report."""
    title: str
    content: str
    data: Dict[str, Any] = field(default_factory=dict)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    charts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ComplianceReport:
    """A complete compliance report."""
    metadata: ReportMetadata
    title: str
    summary: str
    sections: List[ReportSection] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            "metadata": self.metadata.to_dict(),
            "title": self.title,
            "summary": self.summary,
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "data": s.data,
                    "tables": s.tables,
                    "charts": s.charts,
                }
                for s in self.sections
            ],
            "findings": self.findings,
            "recommendations": self.recommendations,
            "raw_data": self.raw_data,
        }


class ReportGenerator(ABC):
    """Abstract base for report generators."""

    @abstractmethod
    def generate(self, report: ComplianceReport) -> bytes:
        """Generate report in the specific format."""
        pass


class JSONReportGenerator(ReportGenerator):
    """Generate JSON format reports."""

    def generate(self, report: ComplianceReport) -> bytes:
        """Generate JSON report."""
        data = report.to_dict()
        return json.dumps(data, indent=2, default=str).encode()


class HTMLReportGenerator(ReportGenerator):
    """Generate HTML format reports."""

    def generate(self, report: ComplianceReport) -> bytes:
        """Generate HTML report."""
        html = self._build_html(report)
        return html.encode()

    def _build_html(self, report: ComplianceReport) -> str:
        """Build HTML content."""
        sections_html = ""
        for section in report.sections:
            tables_html = ""
            for table in section.tables:
                tables_html += self._render_table(table)

            sections_html += f"""
            <section>
                <h2>{section.title}</h2>
                <p>{section.content}</p>
                {tables_html}
            </section>
            """

        findings_html = ""
        if report.findings:
            findings_html = "<section><h2>Findings</h2><ul>"
            for finding in report.findings:
                severity = finding.get("severity", "info")
                desc = finding.get("description", "")
                findings_html += f'<li class="finding-{severity}">{desc}</li>'
            findings_html += "</ul></section>"

        recommendations_html = ""
        if report.recommendations:
            recommendations_html = "<section><h2>Recommendations</h2><ul>"
            for rec in report.recommendations:
                recommendations_html += f"<li>{rec}</li>"
            recommendations_html += "</ul></section>"

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        header {{
            border-bottom: 2px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{ color: #1e40af; }}
        h2 {{ color: #1e3a8a; border-bottom: 1px solid #e5e7eb; padding-bottom: 10px; }}
        .metadata {{
            background: #f3f4f6;
            padding: 15px;
            border-radius: 8px;
            font-size: 0.9em;
        }}
        .summary {{
            background: #eff6ff;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #2563eb;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background: #f9fafb;
            font-weight: 600;
        }}
        .finding-high {{ color: #dc2626; }}
        .finding-medium {{ color: #d97706; }}
        .finding-low {{ color: #059669; }}
        .finding-info {{ color: #2563eb; }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 0.85em;
            color: #6b7280;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{report.title}</h1>
        <div class="metadata">
            <strong>Report ID:</strong> {report.metadata.report_id}<br>
            <strong>Type:</strong> {report.metadata.report_type.value}<br>
            <strong>Generated:</strong> {report.metadata.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
            {f'<strong>Period:</strong> {report.metadata.period_start.strftime("%Y-%m-%d")} to {report.metadata.period_end.strftime("%Y-%m-%d")}<br>' if report.metadata.period_start and report.metadata.period_end else ''}
        </div>
    </header>

    <div class="summary">
        <h2>Executive Summary</h2>
        <p>{report.summary}</p>
    </div>

    {sections_html}
    {findings_html}
    {recommendations_html}

    <footer>
        <p>This report was automatically generated by the Sardis Compliance System.</p>
        <p>Confidential - For authorized personnel only.</p>
    </footer>
</body>
</html>
        """

    def _render_table(self, table: Dict[str, Any]) -> str:
        """Render a table to HTML."""
        if not table:
            return ""

        headers = table.get("headers", [])
        rows = table.get("rows", [])
        title = table.get("title", "")

        html = ""
        if title:
            html += f"<h3>{title}</h3>"

        html += "<table><thead><tr>"
        for header in headers:
            html += f"<th>{header}</th>"
        html += "</tr></thead><tbody>"

        for row in rows:
            html += "<tr>"
            for cell in row:
                html += f"<td>{cell}</td>"
            html += "</tr>"

        html += "</tbody></table>"
        return html


class PDFReportGenerator(ReportGenerator):
    """Generate PDF format reports using reportlab."""

    def generate(self, report: ComplianceReport) -> bytes:
        """Generate PDF report."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            logger.warning("reportlab not available, falling back to HTML")
            html_gen = HTMLReportGenerator()
            return html_gen.generate(report)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor("#1e40af"),
        )
        story.append(Paragraph(report.title, title_style))

        # Metadata
        meta_style = ParagraphStyle(
            "Metadata",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#6b7280"),
        )
        meta_text = (
            f"Report ID: {report.metadata.report_id}<br/>"
            f"Type: {report.metadata.report_type.value}<br/>"
            f"Generated: {report.metadata.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        if report.metadata.period_start and report.metadata.period_end:
            meta_text += f"<br/>Period: {report.metadata.period_start.strftime('%Y-%m-%d')} to {report.metadata.period_end.strftime('%Y-%m-%d')}"
        story.append(Paragraph(meta_text, meta_style))
        story.append(Spacer(1, 20))

        # Summary
        summary_style = ParagraphStyle(
            "Summary",
            parent=styles["Normal"],
            fontSize=11,
            spaceAfter=20,
            backColor=colors.HexColor("#eff6ff"),
            borderPadding=10,
        )
        story.append(Paragraph("<b>Executive Summary</b>", styles["Heading2"]))
        story.append(Paragraph(report.summary, summary_style))
        story.append(Spacer(1, 20))

        # Sections
        for section in report.sections:
            story.append(Paragraph(section.title, styles["Heading2"]))
            story.append(Paragraph(section.content, styles["Normal"]))

            # Tables
            for table_data in section.tables:
                if table_data.get("headers") and table_data.get("rows"):
                    data = [table_data["headers"]] + table_data["rows"]
                    table = Table(data)
                    table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9fafb")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ]))
                    story.append(Spacer(1, 10))
                    story.append(table)

            story.append(Spacer(1, 15))

        # Findings
        if report.findings:
            story.append(Paragraph("Findings", styles["Heading2"]))
            for finding in report.findings:
                severity = finding.get("severity", "info")
                color_map = {
                    "high": "#dc2626",
                    "medium": "#d97706",
                    "low": "#059669",
                    "info": "#2563eb",
                }
                color = color_map.get(severity, "#333333")
                finding_style = ParagraphStyle(
                    "Finding",
                    parent=styles["Normal"],
                    textColor=colors.HexColor(color),
                )
                story.append(Paragraph(f"- {finding.get('description', '')}", finding_style))
            story.append(Spacer(1, 15))

        # Recommendations
        if report.recommendations:
            story.append(Paragraph("Recommendations", styles["Heading2"]))
            for rec in report.recommendations:
                story.append(Paragraph(f"- {rec}", styles["Normal"]))

        # Build PDF
        doc.build(story)
        return buffer.getvalue()


class CSVReportGenerator(ReportGenerator):
    """Generate CSV format reports for data export."""

    def generate(self, report: ComplianceReport) -> bytes:
        """Generate CSV report."""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Sardis Compliance Report"])
        writer.writerow(["Report ID", report.metadata.report_id])
        writer.writerow(["Type", report.metadata.report_type.value])
        writer.writerow(["Generated", report.metadata.created_at.isoformat()])
        writer.writerow([])

        # Data tables from sections
        for section in report.sections:
            writer.writerow([section.title])
            for table in section.tables:
                if table.get("headers"):
                    writer.writerow(table["headers"])
                for row in table.get("rows", []):
                    writer.writerow(row)
                writer.writerow([])

        return output.getvalue().encode()


class ComplianceReportService:
    """
    High-level service for generating compliance reports.
    """

    def __init__(self):
        self._generators = {
            ReportFormat.JSON: JSONReportGenerator(),
            ReportFormat.HTML: HTMLReportGenerator(),
            ReportFormat.PDF: PDFReportGenerator(),
            ReportFormat.CSV: CSVReportGenerator(),
        }

    def generate_audit_trail_report(
        self,
        entries: List[Dict[str, Any]],
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        format: ReportFormat = ReportFormat.PDF,
    ) -> tuple[bytes, ReportMetadata]:
        """Generate an audit trail report."""
        import uuid

        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # Calculate statistics
        total_entries = len(entries)
        allowed_count = sum(1 for e in entries if e.get("allowed", False))
        denied_count = total_entries - allowed_count

        # Group by provider
        by_provider: Dict[str, int] = {}
        for entry in entries:
            provider = entry.get("provider", "unknown")
            by_provider[provider] = by_provider.get(provider, 0) + 1

        # Group by rule
        by_rule: Dict[str, int] = {}
        for entry in entries:
            rule = entry.get("rule_id", "unknown")
            by_rule[rule] = by_rule.get(rule, 0) + 1

        # Build report
        metadata = ReportMetadata(
            report_id=report_id,
            report_type=ReportType.AUDIT_TRAIL,
            format=format,
            created_at=now,
            period_start=period_start,
            period_end=period_end,
        )

        summary = (
            f"This audit trail report covers {total_entries} compliance decisions. "
            f"{allowed_count} transactions were approved ({100*allowed_count/total_entries:.1f}%) "
            f"and {denied_count} were denied ({100*denied_count/total_entries:.1f}%)."
        )

        sections = [
            ReportSection(
                title="Overview",
                content="Summary of compliance decisions during the reporting period.",
                data={
                    "total_entries": total_entries,
                    "allowed": allowed_count,
                    "denied": denied_count,
                },
                tables=[
                    {
                        "title": "Decisions by Provider",
                        "headers": ["Provider", "Count"],
                        "rows": [[k, str(v)] for k, v in by_provider.items()],
                    },
                    {
                        "title": "Decisions by Rule",
                        "headers": ["Rule ID", "Count"],
                        "rows": [[k, str(v)] for k, v in by_rule.items()],
                    },
                ],
            ),
            ReportSection(
                title="Detailed Entries",
                content="Individual compliance decisions.",
                tables=[
                    {
                        "title": "Recent Decisions",
                        "headers": ["Audit ID", "Mandate ID", "Subject", "Allowed", "Reason", "Time"],
                        "rows": [
                            [
                                entry.get("audit_id", "")[:12],
                                entry.get("mandate_id", "")[:12],
                                entry.get("subject", "")[:20],
                                "Yes" if entry.get("allowed") else "No",
                                entry.get("reason", "-")[:30],
                                entry.get("evaluated_at", "")[:19],
                            ]
                            for entry in entries[:50]  # Limit to 50 for readability
                        ],
                    },
                ],
            ),
        ]

        report = ComplianceReport(
            metadata=metadata,
            title="Compliance Audit Trail Report",
            summary=summary,
            sections=sections,
            raw_data={"entries": entries},
        )

        # Generate output
        generator = self._generators[format]
        content = generator.generate(report)

        metadata.status = ReportStatus.COMPLETED
        metadata.file_size_bytes = len(content)

        return content, metadata

    def generate_risk_assessment_report(
        self,
        risk_data: Dict[str, Any],
        format: ReportFormat = ReportFormat.PDF,
    ) -> tuple[bytes, ReportMetadata]:
        """Generate a risk assessment report."""
        import uuid

        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        metadata = ReportMetadata(
            report_id=report_id,
            report_type=ReportType.RISK_ASSESSMENT,
            format=format,
            created_at=now,
        )

        overall_risk = risk_data.get("overall_risk", "medium")
        risk_factors = risk_data.get("risk_factors", [])

        summary = (
            f"Overall risk assessment: {overall_risk.upper()}. "
            f"{len(risk_factors)} risk factors identified requiring attention."
        )

        findings = []
        for factor in risk_factors:
            findings.append({
                "severity": factor.get("level", "medium"),
                "description": factor.get("description", "Unspecified risk factor"),
            })

        recommendations = risk_data.get("recommendations", [
            "Implement enhanced monitoring for high-risk transactions",
            "Review and update risk thresholds quarterly",
            "Conduct periodic staff training on compliance procedures",
        ])

        sections = [
            ReportSection(
                title="Risk Overview",
                content="Assessment of current risk posture.",
                data={"overall_risk": overall_risk},
                tables=[
                    {
                        "title": "Risk Factors",
                        "headers": ["Factor", "Level", "Impact"],
                        "rows": [
                            [
                                f.get("name", "Unknown"),
                                f.get("level", "medium"),
                                f.get("impact", "moderate"),
                            ]
                            for f in risk_factors
                        ],
                    },
                ],
            ),
        ]

        report = ComplianceReport(
            metadata=metadata,
            title="Risk Assessment Report",
            summary=summary,
            sections=sections,
            findings=findings,
            recommendations=recommendations,
            raw_data=risk_data,
        )

        generator = self._generators[format]
        content = generator.generate(report)

        metadata.status = ReportStatus.COMPLETED
        metadata.file_size_bytes = len(content)

        return content, metadata

    def generate_pep_screening_report(
        self,
        screening_results: List[Dict[str, Any]],
        format: ReportFormat = ReportFormat.PDF,
    ) -> tuple[bytes, ReportMetadata]:
        """Generate a PEP screening report."""
        import uuid

        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        metadata = ReportMetadata(
            report_id=report_id,
            report_type=ReportType.PEP_SCREENING,
            format=format,
            created_at=now,
        )

        total_screened = len(screening_results)
        pep_count = sum(1 for r in screening_results if r.get("is_pep", False))
        edd_required = sum(1 for r in screening_results if r.get("requires_enhanced_due_diligence", False))

        summary = (
            f"PEP screening completed for {total_screened} individuals. "
            f"{pep_count} identified as Politically Exposed Persons. "
            f"{edd_required} require Enhanced Due Diligence."
        )

        sections = [
            ReportSection(
                title="Screening Summary",
                content="Overview of PEP screening results.",
                data={
                    "total_screened": total_screened,
                    "pep_count": pep_count,
                    "edd_required": edd_required,
                },
                tables=[
                    {
                        "title": "Screening Results",
                        "headers": ["Subject", "Is PEP", "Risk Level", "EDD Required"],
                        "rows": [
                            [
                                r.get("subject_name", "Unknown")[:30],
                                "Yes" if r.get("is_pep") else "No",
                                r.get("highest_risk", "low"),
                                "Yes" if r.get("requires_enhanced_due_diligence") else "No",
                            ]
                            for r in screening_results[:100]
                        ],
                    },
                ],
            ),
        ]

        findings = []
        for result in screening_results:
            if result.get("is_pep"):
                findings.append({
                    "severity": "high" if result.get("highest_risk") in ("high", "very_high") else "medium",
                    "description": f"PEP match found for {result.get('subject_name', 'Unknown')}: {result.get('reason', 'N/A')}",
                })

        report = ComplianceReport(
            metadata=metadata,
            title="PEP Screening Report",
            summary=summary,
            sections=sections,
            findings=findings,
            recommendations=[
                "Complete Enhanced Due Diligence for all identified PEPs",
                "Document source of funds for PEP relationships",
                "Implement ongoing monitoring for PEP accounts",
            ] if pep_count > 0 else [],
            raw_data={"results": screening_results},
        )

        generator = self._generators[format]
        content = generator.generate(report)

        metadata.status = ReportStatus.COMPLETED
        metadata.file_size_bytes = len(content)

        return content, metadata

    def generate_sanctions_report(
        self,
        screening_results: List[Dict[str, Any]],
        format: ReportFormat = ReportFormat.PDF,
    ) -> tuple[bytes, ReportMetadata]:
        """Generate a sanctions screening report."""
        import uuid

        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        metadata = ReportMetadata(
            report_id=report_id,
            report_type=ReportType.SANCTIONS_SCREENING,
            format=format,
            created_at=now,
        )

        total_screened = len(screening_results)
        blocked_count = sum(1 for r in screening_results if r.get("should_block", False))
        high_risk_count = sum(
            1 for r in screening_results
            if r.get("risk_level") in ("high", "severe", "blocked")
        )

        summary = (
            f"Sanctions screening completed for {total_screened} entities. "
            f"{blocked_count} blocked due to sanctions matches. "
            f"{high_risk_count} identified as high risk."
        )

        sections = [
            ReportSection(
                title="Screening Summary",
                content="Overview of sanctions screening results.",
                data={
                    "total_screened": total_screened,
                    "blocked_count": blocked_count,
                    "high_risk_count": high_risk_count,
                },
                tables=[
                    {
                        "title": "Screening Results",
                        "headers": ["Entity ID", "Type", "Risk Level", "Sanctioned", "Action"],
                        "rows": [
                            [
                                r.get("entity_id", "Unknown")[:20],
                                r.get("entity_type", "unknown"),
                                r.get("risk_level", "low"),
                                "Yes" if r.get("is_sanctioned") else "No",
                                "BLOCKED" if r.get("should_block") else "Allowed",
                            ]
                            for r in screening_results[:100]
                        ],
                    },
                ],
            ),
        ]

        findings = []
        for result in screening_results:
            if result.get("should_block"):
                findings.append({
                    "severity": "high",
                    "description": f"Sanctions match for {result.get('entity_id', 'Unknown')}: {result.get('reason', 'N/A')}",
                })

        report = ComplianceReport(
            metadata=metadata,
            title="Sanctions Screening Report",
            summary=summary,
            sections=sections,
            findings=findings,
            recommendations=[
                "File SAR for blocked transactions",
                "Review and document all high-risk matches",
                "Update internal blocklist with new matches",
            ] if blocked_count > 0 else [],
            raw_data={"results": screening_results},
        )

        generator = self._generators[format]
        content = generator.generate(report)

        metadata.status = ReportStatus.COMPLETED
        metadata.file_size_bytes = len(content)

        return content, metadata

    def generate_executive_summary(
        self,
        period_start: datetime,
        period_end: datetime,
        audit_entries: List[Dict[str, Any]],
        pep_results: List[Dict[str, Any]],
        sanctions_results: List[Dict[str, Any]],
        format: ReportFormat = ReportFormat.PDF,
    ) -> tuple[bytes, ReportMetadata]:
        """Generate a comprehensive executive summary report."""
        import uuid

        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        metadata = ReportMetadata(
            report_id=report_id,
            report_type=ReportType.EXECUTIVE_SUMMARY,
            format=format,
            created_at=now,
            period_start=period_start,
            period_end=period_end,
        )

        # Calculate metrics
        total_transactions = len(audit_entries)
        approved = sum(1 for e in audit_entries if e.get("allowed"))
        denied = total_transactions - approved

        pep_count = sum(1 for r in pep_results if r.get("is_pep"))
        sanctions_hits = sum(1 for r in sanctions_results if r.get("should_block"))

        summary = (
            f"During the period {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}, "
            f"the compliance system processed {total_transactions} transactions with a {100*approved/total_transactions:.1f}% approval rate. "
            f"{pep_count} PEP matches and {sanctions_hits} sanctions hits were identified."
        )

        sections = [
            ReportSection(
                title="Key Metrics",
                content="High-level compliance metrics for the reporting period.",
                data={
                    "total_transactions": total_transactions,
                    "approval_rate": f"{100*approved/total_transactions:.1f}%",
                    "pep_matches": pep_count,
                    "sanctions_hits": sanctions_hits,
                },
                tables=[
                    {
                        "title": "Summary Statistics",
                        "headers": ["Metric", "Value"],
                        "rows": [
                            ["Total Transactions", str(total_transactions)],
                            ["Approved", str(approved)],
                            ["Denied", str(denied)],
                            ["Approval Rate", f"{100*approved/total_transactions:.1f}%"],
                            ["PEP Matches", str(pep_count)],
                            ["Sanctions Hits", str(sanctions_hits)],
                        ],
                    },
                ],
            ),
        ]

        findings = []
        if denied > total_transactions * 0.1:
            findings.append({
                "severity": "medium",
                "description": f"Denial rate of {100*denied/total_transactions:.1f}% exceeds 10% threshold",
            })
        if sanctions_hits > 0:
            findings.append({
                "severity": "high",
                "description": f"{sanctions_hits} transactions blocked due to sanctions matches",
            })

        report = ComplianceReport(
            metadata=metadata,
            title="Compliance Executive Summary",
            summary=summary,
            sections=sections,
            findings=findings,
            recommendations=[
                "Review denial patterns for potential process improvements",
                "Ensure all sanctions hits have been properly reported",
                "Schedule quarterly compliance review meeting",
            ],
        )

        generator = self._generators[format]
        content = generator.generate(report)

        metadata.status = ReportStatus.COMPLETED
        metadata.file_size_bytes = len(content)

        return content, metadata


def create_report_service() -> ComplianceReportService:
    """Create a compliance report service instance."""
    return ComplianceReportService()
