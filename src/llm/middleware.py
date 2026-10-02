import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from src.core.security.redaction import Redactor, default_redactor
from src.domain.compliance_state import ComplianceRationale, RedactionResult

logger = logging.getLogger(__name__)


class LLMPrivacyMiddleware:
    """
    Interceptor middleware wrapping LLM API calls to enforce GDPR/CCPA data privacy compliance
    and generate explainability rationale for LLM executions.
    """

    def __init__(self, redactor: Optional[Redactor] = None):
        self.redactor = redactor or default_redactor

    def process_prompt(self, prompt: str) -> Tuple[str, RedactionResult]:
        """
        Redacts PII from raw string prompt prior to sending to LLM.
        """
        redaction_result = self.redactor.redact_text(prompt)
        if redaction_result.pii_detected:
            logger.info(
                f"LLMPrivacyMiddleware redacted {redaction_result.total_redactions} PII entities "
                f"from prompt. Types: {list(redaction_result.entities_found.keys())}"
            )
        return redaction_result.redacted_text, redaction_result

    def process_messages(
        self, messages: List[Union[Dict[str, Any], Any]]
    ) -> Tuple[List[Any], RedactionResult]:
        """
        Redacts PII from structured message lists (e.g. LangChain or OpenAI format).
        """
        processed_messages = []
        combined_entities: Dict[str, int] = {}
        total_redactions = 0

        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                if isinstance(content, str):
                    res = self.redactor.redact_text(content)
                    new_msg = dict(msg)
                    new_msg["content"] = res.redacted_text
                    processed_messages.append(new_msg)
                    if res.pii_detected:
                        for k, v in res.entities_found.items():
                            combined_entities[k] = combined_entities.get(k, 0) + v
                        total_redactions += res.total_redactions
                else:
                    processed_messages.append(msg)
            elif hasattr(msg, "content") and isinstance(getattr(msg, "content"), str):
                res = self.redactor.redact_text(msg.content)
                msg.content = res.redacted_text
                processed_messages.append(msg)
                if res.pii_detected:
                    for k, v in res.entities_found.items():
                        combined_entities[k] = combined_entities.get(k, 0) + v
                    total_redactions += res.total_redactions
            else:
                processed_messages.append(msg)

        overall_result = RedactionResult(
            pii_detected=total_redactions > 0,
            entities_found=combined_entities,
            total_redactions=total_redactions,
        )
        return processed_messages, overall_result

    def wrap_llm_call(
        self,
        llm_callable: Callable[..., Any],
        prompt: Union[str, List[Any]],
        *args,
        **kwargs,
    ) -> Tuple[Any, RedactionResult, ComplianceRationale]:
        """
        Wraps an LLM function call:
        1. Redacts prompt input.
        2. Executes LLM callable with sanitized prompt.
        3. Attaches redaction metrics and generates a ComplianceRationale for explainability.
        """
        if isinstance(prompt, str):
            clean_prompt, redaction_res = self.process_prompt(prompt)
            response = llm_callable(clean_prompt, *args, **kwargs)
        elif isinstance(prompt, list):
            clean_msgs, redaction_res = self.process_messages(prompt)
            response = llm_callable(clean_msgs, *args, **kwargs)
        else:
            clean_prompt = str(prompt)
            clean_prompt, redaction_res = self.process_prompt(clean_prompt)
            response = llm_callable(clean_prompt, *args, **kwargs)

        rationale = ComplianceRationale(
            component="LLMPrivacyMiddleware",
            decision="PROMPT_REDACTED_AND_DISPATCHED",
            rationale=(
                f"Prompt processed by Privacy Middleware. PII detected: {redaction_res.pii_detected}. "
                f"Total redactions performed: {redaction_res.total_redactions}."
            ),
            factors=[
                f"Original Prompt Hash: {redaction_res.original_text_hash}",
                f"Entities Masked: {list(redaction_res.entities_found.keys())}",
            ],
        )

        return response, redaction_res, rationale


# Default middleware instance
privacy_middleware = LLMPrivacyMiddleware()


def privacy_interceptor(fn: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for LLM functions to automatically apply PII redaction to the first string/list argument.
    """
    @functools.wraps(fn)
    def wrapper(prompt: Any, *args, **kwargs):
        if isinstance(prompt, str):
            clean_prompt, _ = privacy_middleware.process_prompt(prompt)
            return fn(clean_prompt, *args, **kwargs)
        elif isinstance(prompt, list):
            clean_msgs, _ = privacy_middleware.process_messages(prompt)
            return fn(clean_msgs, *args, **kwargs)
        return fn(prompt, *args, **kwargs)

    return wrapper
