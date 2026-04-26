POLICY_TEMPLATES = {
    "Lumbar MRI": """Policy: Advanced Imaging - Lumbar Spine MRI (Policy #IMG-2024-07)
Covered indications:
1. Persistent LBP >= 6 weeks with failure of conservative therapy (PT >= 4 weeks AND analgesic trial).
2. Neurological deficits (radiculopathy, motor weakness, bowel/bladder dysfunction).
3. Red flag symptoms: unexplained weight loss, fever, history of malignancy.
4. Pre-surgical planning when clinical findings support surgical candidacy.

Not covered:
- Acute LBP < 6 weeks without red flags.
- When prior MRI within 12 months without significant clinical change.

Documentation required:
- Office visit notes documenting clinical findings.
- PT discharge summary or progress notes.
- Medication trial documentation.
- Referring physician attestation.""",
    "Brain MRI": """Policy: Neuroimaging - Brain MRI (Policy #NEURO-2024-03)
Covered indications:
1. New onset headache with red flag symptoms (focal neurological signs, papilledema, new aura, sudden severe headache).
2. Chronic headache refractory to >=3 preventive medications and acute treatments.
3. Headache with atypical features or progression.
4. Pre-treatment evaluation when planning invasive procedures.

Not covered:
- Routine headache evaluation without red flags.
- When prior MRI within 12 months without change.

Documentation required:
- Detailed headache history including frequency, duration, character.
- List of medications tried with durations and outcomes.
- Neurological exam findings.
- Referring neurologist attestation.""",
    "Cardiac Stress Test": """Policy: Cardiac Stress Testing (Policy #CARD-2024-02)
Covered indications:
1. Chest pain or angina equivalent with intermediate/high cardiac risk.
2. Evaluation of known coronary artery disease.
3. Pre-operative assessment for non-cardiac surgery in high-risk patients.
4. Assessment of cardiac function post-myocardial infarction.

Not covered:
- Routine screening without symptoms.
- Low-risk patients with atypical symptoms.

Documentation required:
- Symptom description and cardiac risk factors.
- Prior cardiac workup results.
- Indication for stress testing.""",
    "Colonoscopy": """Policy: Colonoscopy Screening (Policy #GI-2024-01)
Covered indications:
1. Age >=50 for average risk screening.
2. Age >=45 for African American patients.
3. High-risk features: family history, polyps, inflammatory bowel disease.
4. Surveillance following polyp removal or cancer resection.

Not covered:
- Routine screening before eligible age without risk factors.
- Diagnostic colonoscopy without appropriate indications.

Documentation required:
- Age verification.
- Risk factor assessment.
- Prior colonoscopy results if applicable.""",
}

DEMO_DATA = {
    "procedure": "MRI Lumbar Spine without contrast (CPT 72148)",
    "clinical_notes": (
        "Patient: Jane Doe, 47F\n"
        "Presenting complaint: Persistent lower back pain radiating to the left leg for 6 weeks.\n"
        "Pain score: 7/10, worse with sitting and bending forward.\n"
        "Conservative treatment: Completed 4 weeks of physical therapy, ibuprofen 600mg TID - minimal relief.\n"
        "Neurological findings: Mild weakness in left L4/L5 dermatome. Positive straight leg raise at 45 degrees.\n"
        "Prior imaging: X-ray (3 months ago) showed mild disc space narrowing at L4-L5.\n"
        "Referring physician: Dr. Anand Rao, Orthopedic Surgery.\n"
        "Urgency: Routine but clinically indicated for surgical planning."
    ),
    "policy_text": POLICY_TEMPLATES["Lumbar MRI"],
}

MOCK_RESPONSE = {
    "summary": "Patient presents with a 6-week history of lower back pain with left leg radiculopathy, consistent with possible L4-L5 disc herniation. Conservative treatment including physical therapy and NSAIDs has been completed without adequate relief, meeting the foundational criteria for advanced imaging authorization.",
    "policy_match": "HIGH",
    "policy_match_rationale": "The request meets at least 3 of 4 covered indications: persistent LBP >= 6 weeks, completed conservative therapy, and documented neurological deficit with pre-surgical planning intent.",
    "key_findings": [
        "Duration criterion met: 6 weeks of LBP exceeds the minimum policy threshold.",
        "Conservative therapy completed: 4 weeks PT + NSAID trial documented.",
        "Neurological deficit present: L4-L5 motor weakness and positive SLR at 45 degrees.",
        "Prior imaging (X-ray) shows structural changes at L4-L5 supporting clinical suspicion.",
        "Surgical planning intent documented by orthopedic surgeon referral.",
        "No contraindication - no recent MRI within 12 months on file.",
    ],
    "missing_information": [
        "PT discharge summary or formal progress notes not explicitly included.",
        "Medication trial dates and dosing history should be formally documented.",
        "Referring physician attestation letter not mentioned in submission.",
        "Functional limitation assessment (ADL impact) would strengthen clinical necessity.",
    ],
    "recommendation": "APPROVE",
    "recommendation_rationale": "The request clearly meets policy criteria based on duration, failed conservative therapy, documented neurological deficits, and surgical planning intent. Minor documentation gaps do not warrant denial.",
    "action_items": [
        "Request PT progress notes or discharge summary from treating therapist.",
        "Obtain signed attestation from Dr. Anand Rao confirming surgical planning intent.",
        "Verify no prior MRI on record within the past 12 months.",
        "Communicate approval to provider with standard notification timeline.",
    ],
    "confidence_score": 91,
    "turnaround_priority": "STANDARD",
    "estimated_review_time_minutes": 8,
}

MOCK_CASE_QA_RESPONSES = {
    "why approve": (
        "This case leans toward approval because the notes document 6 weeks of back pain, failed conservative treatment, "
        "and a neurologic finding. Those points line up with the lumbar MRI policy. The main gaps are supporting documents, "
        "not the core medical necessity story."
    ),
    "what is missing": (
        "The biggest missing items are PT progress or discharge notes, clearer medication trial details, and a referring provider "
        "attestation. Adding those would reduce follow-up and make the file easier to process straight through."
    ),
    "what should ops do next": (
        "Ops should request the PT documentation and provider attestation first, then verify there was no MRI in the last 12 months. "
        "Those steps close the main avoidable delays in this case."
    ),
}

MOCK_WHAT_IF_RESPONSE = {
    "updated_recommendation": "APPROVE",
    "impact_level": "HIGH",
    "would_change_decision": True,
    "summary": "This update would make the case easier to approve and reduce follow-up work. It closes two of the biggest documentation gaps.",
    "reasoning": [
        "The hypothetical update adds missing support rather than repeating facts already in the note.",
        "That makes the policy match cleaner and reduces the chance of a pend for documentation.",
        "Ops can move with less provider outreach once the added record is in the file.",
    ],
    "ops_impact": "Reviewer confidence goes up and the case becomes more suitable for low-touch handling.",
    "remaining_gaps": [
        "Final provider attestation may still be needed depending on payer rules.",
    ],
}

MOCK_EVIDENCE_MAP = {
    "criteria_map": [
        {
            "criterion": "Persistent LBP >= 6 weeks with failure of conservative therapy (PT >= 4 weeks AND analgesic trial).",
            "status": "MET",
            "note_evidence": [
                "Lower back pain radiating to the left leg for 6 weeks.",
                "Completed 4 weeks of physical therapy.",
                "Ibuprofen 600mg TID with minimal relief.",
            ],
            "reviewer_note": "The duration and conservative treatment requirements are both documented in the note.",
        },
        {
            "criterion": "Neurological deficits (radiculopathy, motor weakness, bowel/bladder dysfunction).",
            "status": "MET",
            "note_evidence": [
                "Mild weakness in left L4/L5 dermatome.",
                "Positive straight leg raise at 45 degrees.",
            ],
            "reviewer_note": "The note contains neurologic findings consistent with radicular involvement.",
        },
        {
            "criterion": "Red flag symptoms: unexplained weight loss, fever, history of malignancy.",
            "status": "MISSING",
            "note_evidence": [],
            "reviewer_note": "No red flag symptoms are documented in the submitted note.",
        },
        {
            "criterion": "Pre-surgical planning when clinical findings support surgical candidacy.",
            "status": "PARTIAL",
            "note_evidence": [
                "Referring physician: Dr. Anand Rao, Orthopedic Surgery.",
                "Urgency: clinically indicated for surgical planning.",
            ],
            "reviewer_note": "Surgical intent is suggested, but a formal attestation or plan is not included.",
        },
    ],
    "documentation_map": [
        {
            "document": "Office visit notes documenting clinical findings.",
            "status": "FOUND",
            "evidence": "The case note includes symptoms, exam findings, prior imaging, and urgency.",
        },
        {
            "document": "PT discharge summary or progress notes.",
            "status": "NOT_FOUND",
            "evidence": "PT is mentioned, but the actual therapy note is not attached.",
        },
        {
            "document": "Medication trial documentation.",
            "status": "FOUND",
            "evidence": "Ibuprofen trial is documented, though dates could be more explicit.",
        },
        {
            "document": "Referring physician attestation.",
            "status": "NOT_FOUND",
            "evidence": "Referring physician is named, but a signed attestation is not present.",
        },
    ],
}
