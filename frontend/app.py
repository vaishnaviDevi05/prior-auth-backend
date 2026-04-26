import json
import sys
from pathlib import Path

import requests
import streamlit as st
from fhirclient import client
from fhirclient.models import condition, observation
from fhirclient.models import patient as p

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend import config as backend_config
from backend import review_tools
from backend.ai_logic import analyze_pa_request, build_evidence_map
from backend.data import DEMO_DATA, POLICY_TEMPLATES

FHIR_SETTINGS = {
    "app_id": "pa-app",
    "api_base": "https://hapi.fhir.org/baseR4",
}

st.set_page_config(
    page_title="Prior Auth Review Assistant",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

backend_config.load_config()

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');

:root {
    --bg: #f5f1ea;
    --panel: #fffdf9;
    --panel-soft: rgba(255, 253, 249, 0.88);
    --line: rgba(42, 51, 62, 0.1);
    --text: #17212b;
    --muted: #5f6b78;
    --navy: #17324d;
    --navy-soft: #254a70;
    --accent: #0d7a6f;
    --success: #1f7a4f;
    --warn: #a36d1f;
    --danger: #a23f38;
    --shadow: 0 18px 48px rgba(31, 46, 61, 0.08);
}

.stApp {
    background:
        radial-gradient(circle at top left, rgba(13, 122, 111, 0.08), transparent 30%),
        radial-gradient(circle at top right, rgba(23, 50, 77, 0.08), transparent 28%),
        linear-gradient(180deg, #f8f5ef 0%, #f3eee6 100%);
    color: var(--text);
    font-family: "IBM Plex Sans", sans-serif;
}

.block-container {
    max-width: 1240px;
    padding-top: 1.4rem;
    padding-bottom: 2rem;
}

h1, h2, h3, h4 {
    font-family: "Manrope", sans-serif;
    color: var(--text);
    letter-spacing: -0.02em;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f8f3ec 0%, #efe7db 100%);
    border-right: 1px solid rgba(23, 50, 77, 0.08);
}

[data-testid="stSidebar"] * {
    color: var(--text) !important;
}

[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox select {
    background: #ffffff !important;
    color: var(--text) !important;
    border: 1px solid rgba(23, 50, 77, 0.12) !important;
}

.hero {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy-soft) 100%);
    color: white;
    border-radius: 28px;
    padding: 1.8rem 2rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
}

.hero-grid {
    display: grid;
    grid-template-columns: 1.8fr 1fr;
    gap: 1rem;
    align-items: end;
}

.eyebrow {
    display: inline-block;
    padding: 0.34rem 0.72rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.86);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.hero h1 {
    color: white;
    margin: 0.8rem 0 0.55rem;
    font-size: 2.7rem;
    line-height: 0.98;
}

.hero p {
    margin: 0;
    color: rgba(255, 255, 255, 0.84);
    max-width: 700px;
    font-size: 1rem;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
}

.metric-card {
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 1rem;
}

.metric-label {
    color: rgba(255, 255, 255, 0.72);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.metric-value {
    margin-top: 0.45rem;
    color: white;
    font-family: "Manrope", sans-serif;
    font-size: 1.7rem;
}

.metric-sub {
    margin-top: 0.35rem;
    color: rgba(255, 255, 255, 0.74);
    font-size: 0.9rem;
}

.status-grid {
    display: grid;
    grid-template-columns: 1.1fr 1.1fr 1fr;
    gap: 0.8rem;
    margin-bottom: 1rem;
}

.status-card, .section-card, .result-card, .empty-card, .sub-card {
    background: var(--panel-soft);
    border: 1px solid var(--line);
    border-radius: 22px;
    box-shadow: var(--shadow);
}

.status-card {
    padding: 1rem 1.1rem;
}

.status-label {
    color: var(--muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.status-value {
    margin-top: 0.36rem;
    color: var(--text);
    font-family: "Manrope", sans-serif;
    font-size: 1.2rem;
}

.status-sub {
    margin-top: 0.24rem;
    color: var(--muted);
    font-size: 0.92rem;
}

.section-card {
    padding: 1rem 1.1rem;
    margin-bottom: 0.8rem;
}

.section-title {
    margin: 0;
    font-size: 1.15rem;
}

.section-copy {
    margin-top: 0.3rem;
    color: var(--muted);
    font-size: 0.92rem;
}

.step-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
    margin-bottom: 0.9rem;
}

.step-card {
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 0.95rem 1rem;
}

.step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.7rem;
    height: 1.7rem;
    border-radius: 999px;
    background: rgba(13, 122, 111, 0.12);
    color: var(--accent);
    font-family: "Manrope", sans-serif;
    font-weight: 800;
    margin-bottom: 0.55rem;
}

.step-title {
    font-family: "Manrope", sans-serif;
    font-size: 1rem;
    color: var(--text);
}

.step-copy {
    margin-top: 0.25rem;
    color: var(--muted);
    font-size: 0.9rem;
}

.action-card {
    background: linear-gradient(135deg, rgba(13, 122, 111, 0.08), rgba(23, 50, 77, 0.08));
}

.stTextInput input, .stTextArea textarea, .stSelectbox select {
    border-radius: 16px !important;
    border: 1px solid rgba(23, 50, 77, 0.12) !important;
    background: rgba(255, 255, 255, 0.96) !important;
    color: var(--text) !important;
}

div.stButton > button {
    border-radius: 14px;
    border: none;
    background: linear-gradient(135deg, var(--accent) 0%, #0a645b 100%);
    color: white;
    font-weight: 700;
    padding: 0.7rem 1rem;
    box-shadow: 0 12px 24px rgba(13, 122, 111, 0.2);
}

.pill {
    display: inline-flex;
    align-items: center;
    padding: 0.3rem 0.74rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
}

.pill-live { background: rgba(31, 122, 79, 0.12); color: var(--success); }
.pill-demo { background: rgba(163, 109, 31, 0.14); color: var(--warn); }
.pill-offline { background: rgba(162, 63, 56, 0.14); color: var(--danger); }
.pill-approve { background: rgba(31, 122, 79, 0.12); color: var(--success); }
.pill-pend { background: rgba(163, 109, 31, 0.14); color: var(--warn); }
.pill-deny { background: rgba(162, 63, 56, 0.14); color: var(--danger); }
.pill-high { background: rgba(13, 122, 111, 0.12); color: var(--accent); }
.pill-medium { background: rgba(163, 109, 31, 0.14); color: var(--warn); }
.pill-low { background: rgba(162, 63, 56, 0.14); color: var(--danger); }

.result-card {
    padding: 1rem 1.05rem;
    margin-bottom: 0.85rem;
}

.result-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: flex-start;
    margin-bottom: 0.55rem;
}

.list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.15rem;
}

.list-header .card-label {
    margin-bottom: 0;
}

.card-label {
    color: var(--muted);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.25rem;
}

.stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
    margin-bottom: 0.6rem;
}

.stat-box {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 0.85rem;
}

.stat-box strong {
    display: block;
    margin-top: 0.25rem;
    font-family: "Manrope", sans-serif;
    font-size: 1.45rem;
    color: var(--text);
}

.sub-card {
    background: rgba(255, 255, 255, 0.84);
    padding: 0.8rem 0.9rem;
    margin-top: 0.55rem;
}

.sub-card ul {
    margin: 0.2rem 0 0;
    padding-left: 1.1rem;
}

.sub-card li {
    margin-bottom: 0.28rem;
    color: var(--text);
}

.footer-note {
    margin-top: 0.18rem;
    color: var(--muted);
    font-size: 0.92rem;
}

.empty-card {
    padding: 2rem;
    text-align: center;
    color: var(--muted);
}

@media (max-width: 1100px) {
    .hero-grid, .metric-grid, .status-grid, .stats, .step-grid {
        grid-template-columns: 1fr;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


def get_patient_name(pat):
    try:
        if pat.name and len(pat.name) > 0:
            name_obj = pat.name[0]
            given = name_obj.given[0] if hasattr(name_obj, "given") and name_obj.given else ""
            family = name_obj.family if hasattr(name_obj, "family") and name_obj.family else ""
            full = f"{given} {family}".strip()
            return full if full else "Unknown"
        return "Unknown"
    except Exception:
        return "Unknown"


def search_patients(name):
    response = requests.get(
        f"{FHIR_SETTINGS['api_base']}/Patient",
        params={"name": name, "_count": 15},
        timeout=30,
    )
    response.raise_for_status()
    bundle = response.json()

    patients = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource")
        if not resource or resource.get("resourceType") != "Patient":
            continue
        try:
            patients.append(p.Patient(resource, strict=False))
        except Exception:
            continue
    return patients


def load_patient(pid):
    patient_response = requests.get(f"{FHIR_SETTINGS['api_base']}/Patient/{pid}", timeout=30)
    patient_response.raise_for_status()
    patient = p.Patient(patient_response.json(), strict=False)

    smart = client.FHIRClient(settings=FHIR_SETTINGS)
    conds = condition.Condition.where({"patient": pid}).perform_resources(smart.server)
    obs = observation.Observation.where({"patient": pid}).perform_resources(smart.server)
    return patient, conds, obs


def build_notes(patient, conds, obs):
    notes = [f"Patient: {get_patient_name(patient)}"]

    for item in conds[:5]:
        if item.code and hasattr(item.code, "text"):
            notes.append(f"- Condition: {item.code.text}")

    for item in obs[:5]:
        try:
            if item.code and hasattr(item.code, "text") and hasattr(item, "valueQuantity") and item.valueQuantity:
                notes.append(f"- {item.code.text}: {item.valueQuantity.value}")
        except Exception:
            continue

    return "\n".join(notes)


def apply_demo_case():
    st.session_state.procedure = DEMO_DATA["procedure"]
    st.session_state.notes = DEMO_DATA["clinical_notes"]
    st.session_state.policy = DEMO_DATA["policy_text"]
    st.session_state.procedure_input = st.session_state.procedure
    st.session_state.notes_input = st.session_state.notes
    st.session_state.policy_input = st.session_state.policy


def apply_policy_template(name):
    st.session_state.policy = POLICY_TEMPLATES[name]
    if not st.session_state.procedure:
        st.session_state.procedure = name
    st.session_state.procedure_input = st.session_state.procedure
    st.session_state.policy_input = st.session_state.policy


def read_uploaded_text(uploaded_file):
    if uploaded_file is None:
        return ""

    suffix = Path(uploaded_file.name).suffix.lower()
    raw_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")

    if suffix == ".json":
        try:
            payload = json.loads(raw_text)
            if isinstance(payload, dict):
                return payload.get("clinical_notes") or payload.get("policy_text") or json.dumps(payload, indent=2)
        except Exception:
            return raw_text
    return raw_text


def get_inference_status(use_mock):
    azure_ready = backend_config.is_configured()
    deployment = backend_config.get_env_var("AZURE_OPENAI_DEPLOYMENT", "")

    if use_mock:
        return {
            "label": "Demo Mode",
            "detail": "The next run uses a mock response instead of a real-time Azure call.",
            "pill": "pill-demo",
            "deployment": deployment or "Not used",
        }
    if azure_ready:
        return {
            "label": "Real-Time Azure",
            "detail": "The next run will call the configured Azure OpenAI deployment.",
            "pill": "pill-live",
            "deployment": deployment or "Configured",
        }
    return {
        "label": "Azure Not Ready",
        "detail": "Azure environment values are missing, so live inference may fail.",
        "pill": "pill-offline",
        "deployment": "Unavailable",
    }


def run_analysis(procedure, clinical_notes, policy_text, use_mock):
    result = analyze_pa_request(
        procedure=procedure,
        clinical_notes=clinical_notes,
        policy_text=policy_text,
        use_mock=use_mock,
    )
    result["source"] = "mock" if use_mock else "live"
    return result


def run_evidence_map(procedure, clinical_notes, policy_text, analysis_result, use_mock):
    return build_evidence_map(
        procedure=procedure,
        clinical_notes=clinical_notes,
        policy_text=policy_text,
        analysis_result=analysis_result,
        use_mock=use_mock,
    )


def recommendation_pill(value):
    mapping = {
        "APPROVE": "pill-approve",
        "PEND": "pill-pend",
        "DENY": "pill-deny",
    }
    return mapping.get((value or "").upper(), "pill-pend")


def match_pill(value):
    mapping = {
        "HIGH": "pill-high",
        "MEDIUM": "pill-medium",
        "LOW": "pill-low",
    }
    return mapping.get((value or "").upper(), "pill-medium")


def render_result(result, use_mock):
    recommendation = result.get("recommendation", "PEND")
    policy_match = result.get("policy_match", "MEDIUM")
    confidence = int(result.get("confidence_score", 0) or 0)
    eta = result.get("estimated_review_time_minutes", "?")
    priority = result.get("turnaround_priority", "STANDARD")

    st.markdown(
        f"""
<div class="result-card">
  <div class="result-header">
    <div>
      <div class="card-label">Review Result</div>
      <h3 style="margin:0;">Recommendation</h3>
    </div>
    <div class="pill {recommendation_pill(recommendation)}">{recommendation}</div>
  </div>
  <div class="stats">
    <div class="stat-box">
      <div class="card-label">Confidence</div>
      <strong>{confidence}%</strong>
    </div>
    <div class="stat-box">
      <div class="card-label">Policy Match</div>
      <strong>{policy_match}</strong>
    </div>
    <div class="stat-box">
      <div class="card-label">Review Time</div>
      <strong>{eta} min</strong>
      <div class="footer-note">{priority}</div>
    </div>
  </div>
  <div class="sub-card">
    <div class="card-label">Summary</div>
    <div>{result.get("summary", "No summary available.")}</div>
  </div>
  <div class="sub-card">
    <div class="card-label">Why</div>
    <div>{result.get("recommendation_rationale", "No recommendation rationale available.")}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            f"""
<div class="sub-card">
  <div class="list-header">
    <div class="card-label">Key Findings</div>
    <div class="pill {match_pill(policy_match)}">{policy_match} match</div>
  </div>
  <ul>
    {''.join(f'<li>{item}</li>' for item in result.get("key_findings", []))}
  </ul>
</div>
""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            "<div class='sub-card'><div class='card-label'>Missing</div><ul>"
            + "".join(f"<li>{item}</li>" for item in result.get("missing_information", []))
            + "</ul></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='sub-card'><div class='card-label'>Next Steps</div><ul>"
            + "".join(f"<li>{item}</li>" for item in result.get("action_items", []))
            + "</ul></div>",
            unsafe_allow_html=True,
        )


for key, value in {
    "patients": [],
    "notes": "",
    "procedure": "",
    "policy": "",
    "result": None,
    "patient_query": "",
    "case_history": [],
    "evidence_map": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "procedure_input" not in st.session_state:
    st.session_state.procedure_input = st.session_state.procedure

if "notes_input" not in st.session_state:
    st.session_state.notes_input = st.session_state.notes

if "policy_input" not in st.session_state:
    st.session_state.policy_input = st.session_state.policy

if "pending_loaded_notes" not in st.session_state:
    st.session_state.pending_loaded_notes = None

if st.session_state.pending_loaded_notes is not None:
    st.session_state.notes = st.session_state.pending_loaded_notes
    st.session_state.notes_input = st.session_state.pending_loaded_notes
    st.session_state.pending_loaded_notes = None


with st.sidebar:
    st.markdown("## Session")
    use_mock = st.toggle(
        "Demo mode",
        value=not backend_config.is_configured(),
        help="When off, the app uses the configured Azure deployment.",
    )

    st.markdown("### Quick Fill")
    if st.button("Load Demo Case", use_container_width=True):
        apply_demo_case()

    selected_policy = st.selectbox("Policy template", ["Select a template"] + list(POLICY_TEMPLATES.keys()))
    if selected_policy != "Select a template":
        apply_policy_template(selected_policy)

    if st.session_state.case_history:
        st.markdown("### Recent Cases")
        for entry in st.session_state.case_history[-3:][::-1]:
            st.markdown(
                f"""
<div class="sub-card" style="margin-top:0.55rem;">
  <div class="card-label">{entry["timestamp"]}</div>
  <div><strong>{entry["procedure"]}</strong></div>
  <div class="footer-note">{entry["recommendation"]} | {entry["confidence"]}% confidence | readiness {entry["readiness"]}</div>
</div>
""",
                unsafe_allow_html=True,
            )

status = get_inference_status(use_mock)
mode_value = "Live" if status["label"] == "Real-Time Azure" else "Demo"
mode_detail = "Production path ready" if mode_value == "Live" else "Demo path ready"

st.markdown(
    f"""
<section class="hero">
  <div class="hero-grid">
    <div>
      <h1>Prior Authorization review assistant</h1>
      <p>This app helps a reviewer read the case, compare it to policy, and decide what should happen next.</p>
    </div>
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">Mode</div>
        <div class="metric-value">{mode_value}</div>
        <div class="metric-sub">{mode_detail}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Built For</div>
        <div class="metric-value">Review Teams</div>
        <div class="metric-sub">Cleaner intake, faster routing, and clearer next steps</div>
      </div>
    </div>
  </div>
</section>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="status-grid">
  <div class="status-card">
    <div class="status-label">What You Get</div>
    <div class="status-value">Decision Support</div>
    <div class="status-sub">Recommendation, missing items, and next-step routing in one view.</div>
  </div>
  <div class="status-card">
    <div class="status-label">Workflow Benefit</div>
    <div class="status-value">Less Rework</div>
    <div class="status-sub">Cuts manual sorting and makes provider follow-up more consistent.</div>
  </div>
  <div class="status-card">
    <div class="status-label">Current Setup</div>
    <div class="status-value">{status["label"]}</div>
    <div class="status-sub">{status["detail"]}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

tab_intake, tab_results = st.tabs(["Case Intake", "Review Output"])

with tab_intake:
    st.markdown(
        """
<div class="step-grid">
  <div class="step-card">
    <div class="step-number">1</div>
    <div class="step-title">Start a case</div>
    <div class="step-copy">Search or load sample data.</div>
  </div>
  <div class="step-card">
    <div class="step-number">2</div>
    <div class="step-title">Review inputs</div>
    <div class="step-copy">Procedure, notes, and policy.</div>
  </div>
  <div class="step-card">
    <div class="step-number">3</div>
    <div class="step-title">Get decision</div>
    <div class="step-copy">Recommendation, routing, and follow-up.</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="section-card">
  <h3 class="section-title">Patient Search</h3>
  <div class="section-copy">Pull sample patient context into the case.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    search_left, search_right = st.columns([1.1, 0.9], gap="large")

    with search_left:
        name_query = st.text_input(
            "Patient name search",
            value=st.session_state.patient_query,
            placeholder="Search by last name or full name",
        )
        if st.button("Search patients", use_container_width=True):
            st.session_state.patient_query = name_query
            try:
                st.session_state.patients = search_patients(name_query)
                st.success(f"Found {len(st.session_state.patients)} patients.")
            except Exception as exc:
                st.error(f"FHIR search failed: {exc}")

    with search_right:
        st.markdown(
            """
<div class="sub-card" style="margin-top:0;">
  <div class="card-label">Quick demo flow</div>
  <div>Search, pick a patient, and prefill notes.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.caption("For a quick walkthrough, use the demo case in the sidebar.")

    if st.session_state.patients:
        options = [f"{getattr(pat, 'id', 'unknown')} - {get_patient_name(pat)}" for pat in st.session_state.patients]
        selected = st.selectbox("Search results", options, help="Choose a patient to load a short clinical summary into the notes field.")
        if st.button("Load selected patient notes", use_container_width=True):
            pid = selected.split(" - ")[0]
            try:
                patient, conds, obs = load_patient(pid)
                st.session_state.pending_loaded_notes = build_notes(patient, conds, obs)
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to load patient: {exc}")

    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown(
            """
<div class="section-card">
  <h3 class="section-title">Clinical Intake</h3>
  <div class="section-copy">Core case details.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        uploaded_notes = st.file_uploader(
            "Upload clinical notes",
            type=["txt", "md", "json"],
            help="Upload a plain text, markdown, or JSON note file to prefill the clinical notes field.",
        )
        if uploaded_notes is not None:
            st.session_state.notes_input = read_uploaded_text(uploaded_notes)
        st.text_input(
            "Procedure or service",
            key="procedure_input",
            placeholder="MRI Lumbar Spine without contrast (CPT 72148)",
        )
        st.text_area(
            "Clinical notes",
            key="notes_input",
            height=300,
            placeholder="Paste symptoms, failed therapies, objective findings, prior imaging, and referral detail.",
        )

    with right:
        st.markdown(
            """
<div class="section-card">
  <h3 class="section-title">Policy Criteria</h3>
  <div class="section-copy">Policy text used for the decision.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        uploaded_policy = st.file_uploader(
            "Upload policy text",
            type=["txt", "md", "json"],
            help="Upload payer criteria from a text, markdown, or JSON file.",
        )
        if uploaded_policy is not None:
            st.session_state.policy_input = read_uploaded_text(uploaded_policy)
        st.text_area(
            "Policy text",
            key="policy_input",
            height=220,
            placeholder="Paste the policy criteria used for the review.",
        )

    st.session_state.procedure = st.session_state.procedure_input
    st.session_state.notes = st.session_state.notes_input
    st.session_state.policy = st.session_state.policy_input

    st.markdown(
        """
<div class="section-card action-card">
  <h3 class="section-title">Run Review</h3>
  <div class="section-copy">Generate the decision and ops plan.</div>
</div>
""",
        unsafe_allow_html=True,
    )
    analyze = st.button("Run Prior Authorization Analysis", use_container_width=True)

    if analyze:
        if not st.session_state.procedure or not st.session_state.notes or not st.session_state.policy:
            st.error("Complete the procedure, clinical notes, and policy text before running analysis.")
        else:
            payload = {
                "procedure": st.session_state.procedure,
                "clinical_notes": st.session_state.notes,
                "policy_text": st.session_state.policy,
                "use_mock": use_mock,
            }
            try:
                result = run_analysis(**payload)
                st.session_state.result = result
                st.session_state.evidence_map = None
                readiness = review_tools.build_readiness_report(
                    st.session_state.procedure,
                    st.session_state.notes,
                    st.session_state.policy,
                    result,
                )
                st.session_state.case_history.append(
                    review_tools.build_case_history_entry(st.session_state.procedure, result, readiness)
                )
                st.success("Review complete. Open the results tab.")
            except Exception as exc:
                st.error(f"Analysis request failed: {exc}")

with tab_results:
    if st.session_state.result:
        readiness = review_tools.build_readiness_report(
            st.session_state.procedure,
            st.session_state.notes,
            st.session_state.policy,
            st.session_state.result,
        )
        ops_summary = review_tools.build_ops_summary(
            st.session_state.procedure,
            st.session_state.notes,
            st.session_state.policy,
            st.session_state.result,
            readiness,
        )

        render_result(st.session_state.result, use_mock)

        route_col, followup_col = st.columns(2, gap="large")
        with route_col:
            st.markdown(
                """
<div class="section-card">
  <h3 class="section-title">Routing</h3>
  <div class="section-copy">Best next step for this case.</div>
</div>
""",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Route:** {ops_summary['route']}")
            st.write(ops_summary["route_reason"])
            st.write(f"- Confidence: {int(st.session_state.result.get('confidence_score', 0) or 0)}%")
            st.write(f"- Policy match: {st.session_state.result.get('policy_match', 'MEDIUM')}")
            st.write(f"- Coverage: {ops_summary['documentation_coverage']}")
            st.write(f"- Time saved: {ops_summary['manual_savings_minutes']} minutes")

        with followup_col:
            st.markdown(
                """
<div class="section-card">
  <h3 class="section-title">Follow-Up</h3>
  <div class="section-copy">What to request next.</div>
</div>
""",
                unsafe_allow_html=True,
            )
            if ops_summary["outreach_checklist"]:
                for item in ops_summary["outreach_checklist"]:
                    st.write(f"- {item}")
            else:
                st.write("- No follow-up needed.")
            if readiness["gaps"]:
                for item in readiness["gaps"][:2]:
                    st.write(f"- Watch item: {item}")

        st.markdown(
            """
<div class="section-card">
  <h3 class="section-title">Policy-to-Evidence Map</h3>
  <div class="section-copy">Shows which policy points are supported by the note.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("Generate Evidence Map", use_container_width=True):
            try:
                st.session_state.evidence_map = run_evidence_map(
                    st.session_state.procedure,
                    st.session_state.notes,
                    st.session_state.policy,
                    st.session_state.result,
                    use_mock,
                )
            except Exception as exc:
                st.error(f"Evidence mapping failed: {exc}")

        if st.session_state.evidence_map:
            evidence_map = st.session_state.evidence_map
            criteria_col, docs_col = st.columns(2, gap="large")
            with criteria_col:
                st.write("Criteria")
                for item in evidence_map.get("criteria_map", []):
                    st.markdown(
                        f"""
<div class="sub-card">
  <div class="list-header" style="margin-bottom:0.3rem;">
    <div class="card-label">Criterion</div>
    <div class="pill {match_pill('HIGH' if item.get('status') == 'MET' else 'MEDIUM' if item.get('status') == 'PARTIAL' else 'LOW')}">{item.get("status", "MISSING")}</div>
  </div>
  <div><strong>{item.get("criterion", "")}</strong></div>
  <div class="footer-note" style="margin-top:0.45rem;">{item.get("reviewer_note", "")}</div>
</div>
""",
                        unsafe_allow_html=True,
                    )
                    if item.get("note_evidence"):
                        for evidence in item.get("note_evidence", []):
                            st.write(f"- {evidence}")
                    else:
                        st.write("- No direct support found in the note.")

            with docs_col:
                st.write("Documents")
                for item in evidence_map.get("documentation_map", []):
                    status_text = item.get("status", "NOT_FOUND")
                    pill_class = "pill-approve" if status_text == "FOUND" else "pill-deny"
                    st.markdown(
                        f"""
<div class="sub-card">
  <div class="list-header" style="margin-bottom:0.3rem;">
    <div class="card-label">Required document</div>
    <div class="pill {pill_class}">{status_text}</div>
  </div>
  <div><strong>{item.get("document", "")}</strong></div>
  <div class="footer-note" style="margin-top:0.45rem;">{item.get("evidence", "")}</div>
</div>
""",
                        unsafe_allow_html=True,
                    )

    else:
        st.markdown(
            """
<div class="empty-card">
  <h3>Run a case</h3>
  <p>Decision, routing, and follow-up will appear here.</p>
</div>
""",
            unsafe_allow_html=True,
        )

