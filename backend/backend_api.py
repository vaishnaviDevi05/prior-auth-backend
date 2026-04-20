from typing import Optional

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fhirclient import client
from fhirclient.models import condition, observation
from fhirclient.models import patient as p
from pydantic import BaseModel

from . import config
from .ai_logic import analyze_pa_request
from .components import get_patient_name
from .data import POLICY_TEMPLATES

config.load_config()

FHIR_SETTINGS = {
    "app_id": "pa-app",
    "api_base": "https://hapi.fhir.org/baseR4",
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend_api")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    procedure: str
    clinical_notes: str
    policy_text: str
    use_mock: Optional[bool] = False


class PatientSearchRequest(BaseModel):
    name: str


class LoadPatientRequest(BaseModel):
    patient_id: str


@app.post("/search_patient")
def search_patient(req: PatientSearchRequest):
    import requests

    response = requests.get(
        f"{FHIR_SETTINGS['api_base']}/Patient",
        params={"name": req.name, "_count": 15},
        timeout=30,
    )
    response.raise_for_status()
    bundle = response.json()

    results = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource")
        if not resource or resource.get("resourceType") != "Patient":
            continue
        try:
            results.append(p.Patient(resource, strict=False))
        except Exception:
            continue

    patients = [
        {"id": getattr(pat, "id", "unknown"), "name": get_patient_name(pat)}
        for pat in results
    ]
    return {"patients": patients}


@app.post("/load_patient")
def load_patient(req: LoadPatientRequest):
    import requests

    patient_response = requests.get(f"{FHIR_SETTINGS['api_base']}/Patient/{req.patient_id}", timeout=30)
    patient_response.raise_for_status()
    patient = p.Patient(patient_response.json(), strict=False)

    smart = client.FHIRClient(settings=FHIR_SETTINGS)
    conds = condition.Condition.where({"patient": req.patient_id}).perform_resources(smart.server)
    obs = observation.Observation.where({"patient": req.patient_id}).perform_resources(smart.server)
    notes = []
    name = get_patient_name(patient)
    notes.append(f"Patient: {name}")

    for item in conds[:5]:
        if item.code and hasattr(item.code, "text"):
            notes.append(f"- Condition: {item.code.text}")

    for item in obs[:5]:
        try:
            if item.code and hasattr(item.code, "text") and hasattr(item, "valueQuantity") and item.valueQuantity:
                notes.append(f"- {item.code.text}: {item.valueQuantity.value}")
        except Exception:
            continue

    return {"notes": "\n".join(notes)}


@app.post("/analyze_pa_request")
def analyze_pa(req: AnalyzeRequest):
    logger.info("/analyze_pa_request called with use_mock=%s", req.use_mock)
    try:
        result = analyze_pa_request(
            procedure=req.procedure,
            clinical_notes=req.clinical_notes,
            policy_text=req.policy_text,
            use_mock=req.use_mock,
        )
        result["source"] = "mock" if req.use_mock else "live"
        logger.info(
            "AI result recommendation: %s, source: %s",
            result.get("recommendation", "?"),
            result["source"],
        )
        return result
    except Exception as exc:
        logger.error("Error in analyze_pa_request: %s", exc)
        return {"error": str(exc), "source": "error"}


@app.get("/policy_templates")
def get_policy_templates():
    return POLICY_TEMPLATES


if __name__ == "__main__":
    uvicorn.run("backend.backend_api:app", host="0.0.0.0", port=8000, reload=True)
