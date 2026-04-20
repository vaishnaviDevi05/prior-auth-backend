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
from backend.ai_logic import analyze_pa_request
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
    padding: 1.1rem 1.15rem;
    margin-bottom: 1rem;
}

.result-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
    margin-bottom: 0.8rem;
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
    margin-bottom: 0.8rem;
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
    padding: 0.9rem 1rem;
    margin-top: 0.8rem;
}

.sub-card ul {
    margin: 0.55rem 0 0;
    padding-left: 1.1rem;
}

.sub-card li {
    margin-bottom: 0.42rem;
    color: var(--text);
}

.footer-note {
    margin-top: 0.3rem;
    color: var(--muted);
    font-size: 0.92rem;
}

.empty-card {
    padding: 2rem;
    text-align: center;
    color: var(--muted);
}

@media (max-width: 1100px) {
    .hero-grid, .metric-grid, .status-grid, .stats {
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
    status = get_inference_status(use_mock)
    recommendation = result.get("recommendation", "PEND")
    policy_match = result.get("policy_match", "MEDIUM")
    confidence = int(result.get("confidence_score", 0) or 0)
    eta = result.get("estimated_review_time_minutes", "?")
    priority = result.get("turnaround_priority", "STANDARD")
    source = result.get("source", "mock" if use_mock else "live")
    source_label = "Azure realtime call" if source == "live" else "Demo response"

    st.markdown(
        f"""
<div class="result-card">
  <div class="result-header">
    <div>
      <div class="card-label">Decision Summary</div>
      <h3 style="margin:0;">Prior Authorization Recommendation</h3>
      <div class="footer-note">{source_label}</div>
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
    <div class="card-label">Inference Status</div>
    <div class="pill {status["pill"]}">{status["label"]}</div>
    <div class="footer-note">{status["detail"]}</div>
  </div>
  <div class="sub-card">
    <div class="card-label">Clinical Summary</div>
    <div>{result.get("summary", "No summary available.")}</div>
  </div>
  <div class="sub-card">
    <div class="card-label">Recommendation Rationale</div>
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
  <div class="result-header" style="margin-bottom:0;">
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
            "<div class='sub-card'><div class='card-label'>Missing Information</div><ul>"
            + "".join(f"<li>{item}</li>" for item in result.get("missing_information", []))
            + "</ul></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='sub-card'><div class='card-label'>Action Items</div><ul>"
            + "".join(f"<li>{item}</li>" for item in result.get("action_items", []))
            + "</ul></div>",
            unsafe_allow_html=True,
        )

    st.download_button(
        "Download analysis JSON",
        data=json.dumps(result, indent=2),
        file_name="pa_result.json",
    )


for key, value in {
    "patients": [],
    "notes": "",
    "procedure": "",
    "policy": "",
    "result": None,
    "patient_query": "",
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
    use_mock = st.toggle("Demo mode", value=False, help="When off, the app uses the configured Azure deployment.")

    st.markdown("### Quick Fill")
    if st.button("Load Demo Case", use_container_width=True):
        apply_demo_case()

    selected_policy = st.selectbox("Policy template", ["Select a template"] + list(POLICY_TEMPLATES.keys()))
    if selected_policy != "Select a template":
        apply_policy_template(selected_policy)

status = get_inference_status(use_mock)
mode_value = "Live" if status["label"] == "Real-Time Azure" else "Demo"
mode_detail = "Azure-backed recommendation flow" if mode_value == "Live" else "Stable mock output for demos"

st.markdown(
    f"""
<section class="hero">
  <div class="hero-grid">
    <div>
      <div class="eyebrow">Prior Authorization Review Assistant</div>
      <h1>Prior Auth Review Assistant</h1>
      <p>Review clinical notes against policy criteria</p>
    </div>
    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">Inference</div>
        <div class="metric-value">{mode_value}</div>
        <div class="metric-sub">{mode_detail}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Audience</div>
        <div class="metric-value">UM Teams</div>
        <div class="metric-sub">Clinical reviewers, payer operations, utilization management</div>
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
    <div class="status-label">Inference Status</div>
    <div class="status-value">{status["label"]}</div>
    <div class="status-sub">{status["detail"]}</div>
  </div>
  <div class="status-card">
    <div class="status-label">Azure Deployment</div>
    <div class="status-value">{status["deployment"]}</div>
    <div class="status-sub">Shown only to indicate whether real-time Azure inference is configured.</div>
  </div>
  <div class="status-card">
    <div class="status-label">Execution Path</div>
    <div class="status-value">In-App Analysis</div>
    <div class="status-sub">The deployed Streamlit app calls Azure directly without a separate backend service.</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

tab_intake, tab_results = st.tabs(["Case Intake", "Review Output"])

with tab_intake:
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown(
            """
<div class="section-card">
  <h3 class="section-title">Clinical Intake</h3>
  <div class="section-copy">Enter the requested procedure and the clinical notes that support medical necessity.</div>
</div>
""",
            unsafe_allow_html=True,
        )
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
  <div class="section-copy">Paste payer policy language or select a template from the sidebar.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.text_area(
            "Policy text",
            key="policy_input",
            height=220,
            placeholder="Paste the policy criteria used for the review.",
        )

        with st.expander("Optional FHIR enrichment", expanded=False):
            st.markdown("Search the public HAPI FHIR server and load patient notes into this case.")
            name_query = st.text_input("Patient name", value=st.session_state.patient_query, placeholder="Smith")
            if st.button("Search patient", use_container_width=True):
                st.session_state.patient_query = name_query
                try:
                    st.session_state.patients = search_patients(name_query)
                    st.success(f"Found {len(st.session_state.patients)} patients.")
                except Exception as exc:
                    st.error(f"FHIR search failed: {exc}")

            if st.session_state.patients:
                options = [f"{getattr(pat, 'id', 'unknown')} - {get_patient_name(pat)}" for pat in st.session_state.patients]
                selected = st.selectbox("Select patient", options)
                if st.button("Load patient notes", use_container_width=True):
                    pid = selected.split(" - ")[0]
                    try:
                        patient, conds, obs = load_patient(pid)
                        st.session_state.pending_loaded_notes = build_notes(patient, conds, obs)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to load patient: {exc}")

    st.session_state.procedure = st.session_state.procedure_input
    st.session_state.notes = st.session_state.notes_input
    st.session_state.policy = st.session_state.policy_input

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
                st.success("Analysis complete. Review Output now shows the recommendation.")
            except Exception as exc:
                st.error(f"Analysis request failed: {exc}")

with tab_results:
    if st.session_state.result:
        render_result(st.session_state.result, use_mock)
    else:
        st.markdown(
            """
<div class="empty-card">
  <h3>Waiting for analysis</h3>
  <p>Run a case from the intake tab to see the recommendation, policy match, and action items here.</p>
</div>
""",
            unsafe_allow_html=True,
        )
