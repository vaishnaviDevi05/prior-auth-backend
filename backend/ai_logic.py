import json
import os

from openai import AzureOpenAI

from . import config as backend_config
from .data import MOCK_CASE_QA_RESPONSES, MOCK_EVIDENCE_MAP, MOCK_RESPONSE, MOCK_WHAT_IF_RESPONSE
from .prompts import (
    CASE_QA_PROMPT,
    CASE_QA_SYSTEM_PROMPT,
    EVIDENCE_MAP_PROMPT,
    EVIDENCE_MAP_SYSTEM_PROMPT,
    PA_PROMPT,
    SYSTEM_PROMPT,
    WHAT_IF_PROMPT,
    WHAT_IF_SYSTEM_PROMPT,
)


def _build_client() -> AzureOpenAI:
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT",
    ]
    missing = [var for var in required_vars if not backend_config._is_real_config_value(os.getenv(var, ""))]
    if missing:
        raise Exception(
            "Azure OpenAI is not configured with real credentials. "
            "Use Demo mode or update backend/config.json with a real endpoint, API key, deployment, and API version."
        )

    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


def _mock_case_answer(question: str, result: dict | None) -> str:
    lowered = (question or "").lower()
    for key, value in MOCK_CASE_QA_RESPONSES.items():
        if key in lowered:
            return value

    recommendation = (result or {}).get("recommendation", "PEND")
    summary = (result or {}).get("summary", "The current case supports a preliminary review.")
    return (
        f"Current recommendation: {recommendation}. {summary} "
        "For a demo answer, try asking why the case was approved, what is missing, or what ops should do next."
    )


def analyze_pa_request(procedure: str, clinical_notes: str, policy_text: str, use_mock: bool = False) -> dict:
    """
    Analyze a prior authorization request using Azure OpenAI.
    """
    import logging

    logger = logging.getLogger("ai_logic")
    logger.info("analyze_pa_request called with use_mock=%s", use_mock)
    if use_mock:
        logger.info("Returning MOCK_RESPONSE")
        return MOCK_RESPONSE

    try:
        client = _build_client()

        user_prompt = PA_PROMPT.format(
            procedure=procedure,
            clinical_notes=clinical_notes,
            policy_text=policy_text,
        )

        logger.info("Prompt sent to Azure OpenAI: %s...", user_prompt[:200])

        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        logger.info("Raw AI response: %s...", content[:200])

        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]

        result = json.loads(content.strip())

        required_fields = [
            "summary",
            "policy_match",
            "policy_match_rationale",
            "key_findings",
            "missing_information",
            "recommendation",
            "recommendation_rationale",
            "action_items",
            "confidence_score",
            "turnaround_priority",
            "estimated_review_time_minutes",
        ]

        for field in required_fields:
            if field not in result:
                logger.error("Missing required field: %s", field)
                raise ValueError(f"Missing required field: {field}")

        logger.info("AI recommendation: %s", result.get("recommendation", "?"))
        return result

    except json.JSONDecodeError as exc:
        logger.error("AI response was not valid JSON: %s", str(exc))
        raise Exception(f"AI response was not valid JSON: {str(exc)}")
    except Exception as exc:
        error_text = str(exc)
        logger.error("AI analysis failed: %s", error_text)
        if "Connection error" in error_text:
            raise Exception(
                "Unable to reach Azure OpenAI. Check that backend/config.json contains a real Azure endpoint and key, "
                "or switch on Demo mode for a mock response."
            )
        raise Exception(f"AI analysis failed: {error_text}")


def answer_case_question(
    procedure: str,
    clinical_notes: str,
    policy_text: str,
    analysis_result: dict,
    question: str,
    use_mock: bool = False,
) -> str:
    import logging

    logger = logging.getLogger("ai_logic")
    logger.info("answer_case_question called with use_mock=%s", use_mock)

    if use_mock:
        return _mock_case_answer(question, analysis_result)

    try:
        client = _build_client()
        prompt = CASE_QA_PROMPT.format(
            procedure=procedure,
            clinical_notes=clinical_notes,
            policy_text=policy_text,
            analysis_result=json.dumps(analysis_result, indent=2),
            question=question,
        )

        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": CASE_QA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=350,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        error_text = str(exc)
        logger.error("Case question failed: %s", error_text)
        if "Connection error" in error_text:
            raise Exception(
                "Unable to reach Azure OpenAI for case Q&A. Use Demo mode or check the Azure endpoint and key."
            )
        raise Exception(f"Case question failed: {error_text}")


def simulate_case_update(
    procedure: str,
    clinical_notes: str,
    policy_text: str,
    analysis_result: dict,
    scenario: str,
    use_mock: bool = False,
) -> dict:
    import logging

    logger = logging.getLogger("ai_logic")
    logger.info("simulate_case_update called with use_mock=%s", use_mock)

    if use_mock:
        response = dict(MOCK_WHAT_IF_RESPONSE)
        lowered = (scenario or "").lower()
        if "no pt" in lowered or "still missing" in lowered:
            response["updated_recommendation"] = "PEND"
            response["would_change_decision"] = False
            response["impact_level"] = "LOW"
            response["summary"] = "This scenario does not materially improve the case because it does not close the main documentation gaps."
            response["ops_impact"] = "Ops would still need outreach before a clean decision."
        return response

    try:
        client = _build_client()
        prompt = WHAT_IF_PROMPT.format(
            procedure=procedure,
            clinical_notes=clinical_notes,
            policy_text=policy_text,
            analysis_result=json.dumps(analysis_result, indent=2),
            scenario=scenario,
        )
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": WHAT_IF_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=500,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())
    except json.JSONDecodeError as exc:
        raise Exception(f"What-if response was not valid JSON: {str(exc)}")
    except Exception as exc:
        error_text = str(exc)
        logger.error("What-if simulation failed: %s", error_text)
        if "Connection error" in error_text:
            raise Exception(
                "Unable to reach Azure OpenAI for what-if simulation. Use Demo mode or check the Azure endpoint and key."
            )
        raise Exception(f"What-if simulation failed: {error_text}")


def build_evidence_map(
    procedure: str,
    clinical_notes: str,
    policy_text: str,
    analysis_result: dict,
    use_mock: bool = False,
) -> dict:
    import logging

    logger = logging.getLogger("ai_logic")
    logger.info("build_evidence_map called with use_mock=%s", use_mock)

    if use_mock:
        return dict(MOCK_EVIDENCE_MAP)

    try:
        client = _build_client()
        prompt = EVIDENCE_MAP_PROMPT.format(
            procedure=procedure,
            clinical_notes=clinical_notes,
            policy_text=policy_text,
            analysis_result=json.dumps(analysis_result, indent=2),
        )
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": EVIDENCE_MAP_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=900,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())
    except json.JSONDecodeError as exc:
        raise Exception(f"Evidence map response was not valid JSON: {str(exc)}")
    except Exception as exc:
        error_text = str(exc)
        logger.error("Evidence map failed: %s", error_text)
        if "Connection error" in error_text:
            raise Exception(
                "Unable to reach Azure OpenAI for evidence mapping. Use Demo mode or check the Azure endpoint and key."
            )
        raise Exception(f"Evidence map failed: {error_text}")
