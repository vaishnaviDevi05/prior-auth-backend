import json
import os

from openai import AzureOpenAI

from .data import MOCK_RESPONSE
from .prompts import PA_PROMPT, SYSTEM_PROMPT


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

    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error("Missing Azure OpenAI environment variables: %s", missing)
        raise Exception(f"Missing Azure OpenAI environment variables: {missing}")

    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )

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
        logger.error("AI analysis failed: %s", str(exc))
        raise Exception(f"AI analysis failed: {str(exc)}")
