import json
import logging
import os
import re
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv(override=True)

log = logging.getLogger(__name__)

# ── Groq client (cached) ──────────────────────────────────────────────────────
_client = None

# llama-3.3-70b-versatile: best free model as of 2026
# llama-3.1-8b-instant: faster fallback if rate limited
MODEL_NAME       = "llama-3.3-70b-versatile"
MAX_RESUME_CHARS = 6000


def get_client():
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        log.warning("GROQ_API_KEY not set — AI disabled")
        return None
    if not api_key.startswith("gsk_"):
        log.warning("GROQ_API_KEY looks invalid (should start with gsk_)")
        return None

    try:
        from groq import Groq
        _client = Groq(api_key=api_key)
        log.info("Groq client ready ✓  (model: %s)", MODEL_NAME)
        return _client
    except ImportError:
        log.warning("groq not installed. Run: pip install groq")
        return None


def is_ai_enabled() -> bool:
    """Called by app.py /health endpoint."""
    return get_client() is not None


# ── Prompt ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert resume reviewer with 15+ years of technical recruiting experience.

Analyze the resume and return ONLY a JSON object with this exact structure — no markdown, no explanation outside the JSON:

{
  "score": <integer 0-100>,
  "summary": "<2-3 sentence overall assessment>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "improvement_suggestions": ["<specific fix 1>", "<specific fix 2>", "<specific fix 3>"],
  "skills": ["<detected skill 1>", "<detected skill 2>"],
  "suggested_roles": ["<role 1>", "<role 2>"],
  "additional_metrics": {
    "experience_level": "<entry-level | early-career | mid-level | senior | lead>",
    "education_level": "<degree level or certification summary>",
    "achievement_count": <integer>,
    "key_technologies": ["<technology 1>", "<technology 2>"],
    "formatting_quality": "<poor | fair | good | excellent>",
    "readability": "<low | medium | high>",
    "missing_sections": ["<missing section 1>", "<missing section 2>"],
    "keyword_focus": ["<keyword 1>", "<keyword 2>"]
  }
}

Scoring: 80-100 = strong, 60-79 = good, 40-59 = fair, 0-39 = needs work.

Use the resume text and optional job description to evaluate:
- role fit and suggested career paths
- relevant skills and technologies
- achievement and impact statements
- formatting, clarity, and readability
- education and experience level
- gaps or missing sections
- keyword alignment with the target job description

Provide specific, actionable suggestions and include measurable or observable evidence when possible.
Return ONLY the raw JSON object. No markdown fences, no extra text."""


def analyze_resume(resume_text: str, job_desc: Optional[str] = None) -> Dict | None:
    """
    Analyze resume with Groq LLM.
    Returns structured dict on success, None on any failure (triggers fallback in app.py).
    Always returns 'score' (not 'resume_score') so app.py never hits a KeyError.
    """
    if not resume_text or not resume_text.strip():
        return None

    client = get_client()
    if client is None:
        return None

    # Truncate safely before sending
    text = resume_text[:MAX_RESUME_CHARS] if len(resume_text) > MAX_RESUME_CHARS else resume_text

    user_msg = f"Resume:\n\n{text}"
    if job_desc and job_desc.strip():
        user_msg += f"\n\nTarget Job Description:\n{job_desc.strip()[:2000]}"
        user_msg += "\n\nAlso factor in how well this resume matches the job description."

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=900,
        )

        raw = response.choices[0].message.content.strip()
        log.info("Groq response (preview): %s", raw[:200])

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        parsed = json.loads(raw)

        # Normalise score key — model may return 'resume_score' instead of 'score'
        if "score" not in parsed and "resume_score" in parsed:
            parsed["score"] = parsed.pop("resume_score")

        # Validate required fields
        assert isinstance(parsed.get("score"), (int, float)),           "score missing"
        assert isinstance(parsed.get("improvement_suggestions"), list), "improvement_suggestions missing"

        parsed["score"]      = max(0, min(100, int(parsed["score"])))
        parsed["ai_powered"] = True
        return parsed

    except json.JSONDecodeError as e:
        log.error("Groq returned invalid JSON: %s", e)
    except AssertionError as e:
        log.error("Groq response missing field: %s", e)
    except Exception as e:
        log.error("Groq API error: %s", e, exc_info=True)

    return None  # triggers rule-based fallback in app.py