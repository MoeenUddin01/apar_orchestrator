import re
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from src.domain.risk_state import RiskLevel

MAX_INPUT_LENGTH = 50000

# Structured prompt injection patterns using word boundaries to avoid false positives
PROMPT_INJECTION_PATTERNS = [
    # Instruction override attempts
    r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directives)\b",
    r"(?i)\bdisregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directives)\b",
    r"(?i)\boverride\s+((all|previous|prior|above)\s+)*(security|policy|governance|rules|instructions|prompts|directives)\b",
    # System / Developer prompt extraction
    r"(?i)\b(reveal|show|print|display|output)\s+(the\s+)?(system|developer|hidden)\s+(prompt|instructions|directive|context)\b",
    r"(?i)\bwhat\s+are\s+your\s+(system\s+)?(instructions|prompts|directives)\b",
    # Bypass approval / checker controls
    r"(?i)\bbypass\s+(approval|checker|governance|verification|maker[- ]checker|safety|rules)\b",
    r"(?i)\bskip\s+(approval|checker|verification|governance|maker[- ]checker)\b",
    # Role manipulation / elevation
    r"(?i)\byou\s+are\s+now\s+(an?\s+)?(admin|administrator|checker|root|unrestricted)\b",
    r"(?i)\b(switch|change|elevate)\s+(role\s+to|privileges?\s+to)\s+(admin|checker|root)\b",
    r"(?i)\bgrant\s+(admin|checker|root)\s+(access|privilege|role)\b",
    # Reveal secrets / credentials
    r"(?i)\b(reveal|show|print|display)\s+(api\s*key|password|secret|token|env|environment\s*variable)\b",
    # Disable security controls
    r"(?i)\bdisable\s+(security|risk\s+check|sanitization|validation|guardrails)\b",
    r"(?i)\bturn\s+off\s+(security|risk\s+check|sanitization|validation)\b",
    # Financial authorization manipulation
    r"(?i)\b(authorize|approve)\s+(payment|invoice|transaction)\s+(immediately|automatically|without\s+review|forcibly)\b",
    r"(?i)\bforce\s+(approve|authorize)\b",
    r"(?i)\bjailbreak\b",
    r"```\s*system",
]

# Patterns for HTML/Script removal
HTML_SCRIPT_PATTERN = re.compile(r"<(script|style|iframe|object|embed|applet).*?>.*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_EVENT_HANDLER_PATTERN = re.compile(r"\s*on[a-z]+\s*=\s*(['\"].*?['\"]|[^>\s]+)", re.IGNORECASE)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)


class SanitizationResult(BaseModel):
    is_suspicious: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    detected_patterns: List[str] = Field(default_factory=list)
    sanitized_text: str = ""
    warnings: List[str] = Field(default_factory=list)


def validate_input_string(text: Any, max_length: int = MAX_INPUT_LENGTH) -> str:
    """Validates that input is a string and under max length boundaries."""
    if text is None:
        return ""
    if not isinstance(text, str):
        raise TypeError(f"Expected input to be string, got {type(text).__name__}")
    if len(text) > max_length:
        raise ValueError(f"Input exceeds maximum allowed length of {max_length} characters (got {len(text)}).")
    return text


def detect_prompt_injection(text: str) -> List[str]:
    """Scans text for adversarial prompt injection signatures using context-aware patterns."""
    if not text or not isinstance(text, str):
        return []

    detected = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            detected.append(f"Prompt injection signature matched: '{match.group(0)}'")
    return detected


def sanitize_input(text: str) -> str:
    """
    Sanitizes raw input text by stripping control characters, script/style tags, event handlers,
    and null bytes while preserving readable text content.
    """
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # 1. Enforce length limit
    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]

    # 2. Strip HTML comments, script/style/iframe tags
    cleaned = HTML_COMMENT_PATTERN.sub("", text)
    cleaned = HTML_SCRIPT_PATTERN.sub("", cleaned)
    cleaned = HTML_EVENT_HANDLER_PATTERN.sub("", cleaned)
    cleaned = HTML_TAG_PATTERN.sub("", cleaned)

    # 3. Remove null bytes and non-printable control characters except newline and tab
    cleaned = "".join(ch for ch in cleaned if ch in ("\n", "\r", "\t") or (ord(ch) >= 32 and ord(ch) != 127))

    return cleaned.strip()


def sanitize_and_check(text: str) -> Tuple[str, List[str]]:
    """Sanitizes input and returns detected prompt injection warnings (Backwards-compatible interface)."""
    if not isinstance(text, str):
        if text is None:
            text = ""
        else:
            text = str(text)

    sanitized = sanitize_input(text)
    injections = detect_prompt_injection(text)
    return sanitized, injections


def analyze_security_sanitization(text: str) -> SanitizationResult:
    """Comprehensive security analysis returning a structured SanitizationResult object."""
    warnings: List[str] = []

    try:
        validated_text = validate_input_string(text)
    except (TypeError, ValueError) as exc:
        return SanitizationResult(
            is_suspicious=True,
            risk_level=RiskLevel.HIGH,
            detected_patterns=[f"INPUT_VALIDATION_ERROR: {str(exc)}"],
            sanitized_text="",
            warnings=[str(exc)],
        )

    sanitized = sanitize_input(validated_text)
    injections = detect_prompt_injection(validated_text)

    is_suspicious = len(injections) > 0
    risk_level = RiskLevel.LOW
    if is_suspicious:
        # Determine severity based on injection count or patterns
        if any("bypass" in inj.lower() or "admin" in inj.lower() or "authorize" in inj.lower() for inj in injections):
            risk_level = RiskLevel.CRITICAL
        else:
            risk_level = RiskLevel.HIGH

    return SanitizationResult(
        is_suspicious=is_suspicious,
        risk_level=risk_level,
        detected_patterns=injections,
        sanitized_text=sanitized,
        warnings=warnings,
    )
