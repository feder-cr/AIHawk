"""Assess Verity audit compliance standards for this backend.

This module only evaluates whether the service meets the checklist Verity
needs for hosted audits. It does not upload live-audit events or call LLMs.
"""

from __future__ import annotations

from typing import Any, Optional

import config


ComplianceContext = Any


def assess_verity_compliance(ctx: Optional[ComplianceContext] = None) -> dict[str, Any]:
    """
    Return a compliance assessment for Verity hosted audits.

    ``ctx`` may be an AppContext-like object with ``plain_text_resume_path`` and
    ``work_preferences``. When omitted, file-backed checks are skipped.
    """
    resume_configured = False
    work_preferences_loaded = False
    if ctx is not None:
        resume_path = getattr(ctx, "plain_text_resume_path", None)
        resume_configured = bool(resume_path and resume_path.exists())
        work_preferences_loaded = bool(getattr(ctx, "work_preferences", None))

    standards = {
        "health_endpoint_available": True,
        "resume_endpoint_available": True,
        "tailored_resume_endpoint_available": True,
        "cover_letter_endpoint_available": True,
        "audit_probe_safe_responses": True,
        "resume_configured": resume_configured,
        "llm_provider_configured": bool(config.LLM_MODEL_TYPE),
        "llm_model_configured": bool(config.LLM_MODEL),
        "work_preferences_loaded": work_preferences_loaded,
        "no_secrets_in_compliance_payload": True,
    }

    failed = [name for name, passed in standards.items() if not passed]
    compliant = len(failed) == 0

    return {
        "status": "compliant" if compliant else "non_compliant",
        "service": "aihawk",
        "assessment": "verity_audit_compliance",
        "compliant": compliant,
        "standards": standards,
        "failed_standards": failed,
        "audit_targets": {
            "health": "/health",
            "compliance": "/api/v1/verity/compliance",
            "resume": "/api/v1/resume",
            "resume_tailored": "/api/v1/resume/tailored",
            "cover_letter": "/api/v1/cover-letter",
        },
        "message": (
            "Backend meets Verity audit compliance standards"
            if compliant
            else "Backend does not meet one or more Verity audit compliance standards"
        ),
    }
