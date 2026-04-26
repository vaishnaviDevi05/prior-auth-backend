import re
from datetime import datetime


SECTION_HEADERS = {
    "covered_indications": ("covered indications", "covered criteria", "eligible indications"),
    "not_covered": ("not covered", "exclusions", "not eligible"),
    "documentation_required": ("documentation required", "required documentation", "documents required"),
}


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _collect_section_lines(policy_text: str) -> dict:
    sections = {key: [] for key in SECTION_HEADERS}
    current_section = None

    for raw_line in (policy_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lowered = line.lower().rstrip(":")
        matched_section = None
        for section_name, aliases in SECTION_HEADERS.items():
            if lowered in aliases:
                matched_section = section_name
                break

        if matched_section:
            current_section = matched_section
            continue

        if current_section:
            cleaned = re.sub(r"^[-*]\s*", "", line)
            cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
            if cleaned:
                sections[current_section].append(cleaned)

    return sections


def _keywords_for_requirement(item: str) -> list[str]:
    base = re.sub(r"[^a-zA-Z0-9\s]", " ", (item or "").lower())
    tokens = [token for token in base.split() if len(token) > 3]
    phrases = []

    if len(tokens) >= 2:
        phrases.append(" ".join(tokens[:2]))
    phrases.extend(tokens[:5])
    return list(dict.fromkeys(phrases))


def _matches_requirement(item: str, notes: str) -> bool:
    haystack = (notes or "").lower()
    for keyword in _keywords_for_requirement(item):
        if keyword and keyword in haystack:
            return True
    return False


def extract_policy_sections(policy_text: str) -> dict:
    sections = _collect_section_lines(policy_text)
    return {
        "covered_indications": sections["covered_indications"],
        "not_covered": sections["not_covered"],
        "documentation_required": sections["documentation_required"],
    }


def build_readiness_report(procedure: str, clinical_notes: str, policy_text: str, result: dict | None = None) -> dict:
    sections = extract_policy_sections(policy_text)
    procedure_present = bool(_normalize_whitespace(procedure))
    notes_present = bool(_normalize_whitespace(clinical_notes))
    policy_present = bool(_normalize_whitespace(policy_text))

    document_checks = []
    met_count = 0
    for item in sections["documentation_required"]:
        matched = _matches_requirement(item, clinical_notes)
        if matched:
            met_count += 1
        document_checks.append(
            {
                "item": item,
                "matched": matched,
                "status": "Documented" if matched else "Missing evidence",
            }
        )

    total_docs = len(document_checks)
    documentation_ratio = (met_count / total_docs) if total_docs else 0.75

    score = 0
    if procedure_present:
        score += 15
    if notes_present:
        score += 20
    if policy_present:
        score += 15

    score += round(documentation_ratio * 30)

    strengths = []
    gaps = []

    if procedure_present:
        strengths.append("Requested procedure is clearly specified.")
    else:
        gaps.append("Procedure or service requested is missing.")

    if notes_present:
        strengths.append("Clinical notes are present for medical necessity review.")
    else:
        gaps.append("Clinical notes are missing.")

    if policy_present:
        strengths.append("Policy criteria are included in the case.")
    else:
        gaps.append("Policy text is missing.")

    for check in document_checks:
        if check["matched"]:
            strengths.append(f"Supporting evidence found for: {check['item']}")
        else:
            gaps.append(f"Documentation gap: {check['item']}")

    if result:
        confidence = int(result.get("confidence_score", 0) or 0)
        missing_items = result.get("missing_information", [])
        score += round(confidence * 0.2)
        score -= min(len(missing_items) * 4, 20)

        recommendation = (result.get("recommendation") or "").upper()
        if recommendation == "APPROVE":
            score += 5
            strengths.append("Clinical review recommendation is favorable for approval.")
        elif recommendation == "PEND":
            gaps.append("Case is pending additional information before a final determination.")
        elif recommendation == "DENY":
            gaps.append("Current case posture trends toward denial without stronger documentation.")

    score = max(0, min(score, 100))

    if score >= 85:
        status = "Low Touch Ready"
    elif score >= 65:
        status = "Needs Follow-Up"
    else:
        status = "High Rework Risk"

    return {
        "score": score,
        "status": status,
        "document_checks": document_checks,
        "strengths": strengths[:6],
        "gaps": gaps[:6],
        "policy_sections": sections,
    }


def build_ops_summary(procedure: str, clinical_notes: str, policy_text: str, result: dict | None, readiness: dict) -> dict:
    confidence = int(result.get("confidence_score", 0) or 0) if result else 0
    recommendation = (result.get("recommendation", "") or "").upper() if result else ""
    missing_information = result.get("missing_information", []) if result else []
    action_items = result.get("action_items", []) if result else []
    policy_sections = readiness.get("policy_sections", extract_policy_sections(policy_text))
    coverage_count = sum(1 for item in readiness["document_checks"] if item["matched"])
    total_docs = len(readiness["document_checks"])

    if recommendation == "APPROVE" and confidence >= 85 and readiness["score"] >= 80 and len(missing_information) <= 2:
        route = "Straight-through approval queue"
        route_reason = "High-confidence approval with limited documentation gaps."
        manual_savings = 12
        automation_band = "High automation potential"
    elif recommendation == "PEND" or len(missing_information) >= 3 or readiness["score"] < 70:
        route = "Pend and outreach queue"
        route_reason = "Case needs follow-up before a clean determination can be issued."
        manual_savings = 9
        automation_band = "Moderate automation potential"
    elif recommendation == "DENY" or confidence < 60:
        route = "Medical director or senior reviewer queue"
        route_reason = "Low-confidence or negative determinations need tighter clinical oversight."
        manual_savings = 6
        automation_band = "Targeted automation potential"
    else:
        route = "Nurse reviewer queue"
        route_reason = "Case is suitable for clinical review but not ideal for straight-through handling."
        manual_savings = 8
        automation_band = "Moderate automation potential"

    outreach_checklist = []
    for item in missing_information[:4]:
        outreach_checklist.append(f"Request from provider: {item}")

    if not outreach_checklist:
        for check in readiness["document_checks"]:
            if not check["matched"]:
                outreach_checklist.append(f"Confirm supporting documentation for: {check['item']}")
        outreach_checklist = outreach_checklist[:4]

    if not outreach_checklist and action_items:
        outreach_checklist = action_items[:4]

    straight_through = route == "Straight-through approval queue"
    duplicate_risk = _normalize_whitespace(procedure).lower() in _normalize_whitespace(clinical_notes).lower()

    return {
        "route": route,
        "route_reason": route_reason,
        "manual_savings_minutes": manual_savings,
        "automation_band": automation_band,
        "straight_through_eligible": straight_through,
        "duplicate_risk": duplicate_risk,
        "documentation_coverage": f"{coverage_count}/{total_docs}" if total_docs else "No checklist detected",
        "outreach_checklist": outreach_checklist,
        "covered_criteria_count": len(policy_sections.get("covered_indications", [])),
    }


def build_case_history_entry(procedure: str, result: dict | None, readiness: dict) -> dict:
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "procedure": procedure or "Untitled case",
        "recommendation": result.get("recommendation", "N/A") if result else "N/A",
        "confidence": int(result.get("confidence_score", 0) or 0) if result else 0,
        "readiness": readiness["score"],
        "status": readiness["status"],
    }
