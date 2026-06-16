import re

from app.models.extraction import ExtractedClaim

# Common Indian medical shorthand → expanded form for policy rule matching.
MEDICAL_SHORTHAND: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bt2dm\b", re.IGNORECASE), "Type 2 Diabetes Mellitus"),
    (re.compile(r"\btype\s*2\s*dm\b", re.IGNORECASE), "Type 2 Diabetes Mellitus"),
    (re.compile(r"\bhtn\b", re.IGNORECASE), "Hypertension"),
    (re.compile(r"\buri\b", re.IGNORECASE), "Upper Respiratory Infection"),
    (re.compile(r"\buti\b", re.IGNORECASE), "Urinary Tract Infection"),
    (re.compile(r"\bcopd\b", re.IGNORECASE), "Chronic Obstructive Pulmonary Disease"),
    (re.compile(r"\bgerd\b", re.IGNORECASE), "Gastroesophageal Reflux Disease"),
    (re.compile(r"\bibs\b", re.IGNORECASE), "Irritable Bowel Syndrome"),
]


def _expand_shorthand(text: str | None) -> str | None:
    if not text:
        return text
    expanded = text
    for pattern, replacement in MEDICAL_SHORTHAND:
        expanded = pattern.sub(replacement, expanded)
    return expanded


def normalize_medical_terms(extracted: ExtractedClaim) -> ExtractedClaim:
    return extracted.model_copy(
        update={
            "diagnosis": _expand_shorthand(extracted.diagnosis),
            "treatment": _expand_shorthand(extracted.treatment),
        }
    )
