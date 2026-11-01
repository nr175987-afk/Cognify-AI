import hashlib
import json
import logging
import os
import re
import urllib.request

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11435",
).rstrip("/")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:3b",
)

_api_key = os.getenv("GEMINI_API_KEY")

_gemini_client = (
    genai.Client(api_key=_api_key)
    if _api_key
    else None
)


# ============================================================
# TEXT SPACING CLEANUP
# ============================================================

def _fix_spacing(text):
    """
    Fix a small set of known joined phrases.

    Avoid broad regex rules that may split valid words such
    as 'This', 'main', 'Compare', and 'maintain'.
    """

    if not isinstance(text, str) or not text:
        return text

    replacements = {
        "tomodel": "to model",
        "tothe": "to the",
        "inthe": "in the",
        "ofthe": "of the",
        "isused": "is used",
        "areused": "are used",
        "knownas": "known as",
        "oneormore": "one or more",
        "canbe": "can be",
        "usedto": "used to",
        "suchas": "such as",
        "regressionis": "regression is",
    }

    for wrong, correct in replacements.items():
        text = re.sub(
            re.escape(wrong),
            correct,
            text,
            flags=re.IGNORECASE,
        )

    return text


# ============================================================
# TEXT QUALITY INSTRUCTIONS
# ============================================================

TEXT_QUALITY_REQUIREMENTS = """
IMPORTANT TEXT QUALITY RULES:
- Use correct spelling and normal English word spacing.
- Never insert spaces inside words.
- Do not split words such as This, main, Compare,
  maintain, Explain, join, and into.
- Do not join separate words accidentally.
- Use grammatically correct and readable English.
- Preserve the intended meaning and factual accuracy.
- Use valid Markdown headings, lists, tables, and code blocks.
- Keep code, equations, and technical notation unchanged.
- Return only the requested learning content.
"""


# ============================================================
# DATABASE CACHE
# ============================================================

def _cache_key(task, prompt, schema=None):
    """Create a stable key for reusable AI responses."""

    schema_data = (
        schema.model_json_schema()
        if schema is not None
        else None
    )

    data = json.dumps(
        {
            "version": 3,
            "task": task,
            "prompt": prompt,
            "schema": schema_data,
            "gemini_model": GEMINI_MODEL,
            "ollama_model": OLLAMA_MODEL,
        },
        sort_keys=True,
    )

    return hashlib.sha256(
        data.encode("utf-8")
    ).hexdigest()


def _get_cached_response(key):
    """Read an AI response from the database cache."""

    from .models import AIResponseCache

    item = AIResponseCache.objects.filter(
        cache_key=key
    ).first()

    return item.response_text if item else None


def _save_cached_response(key, content):
    """Save an AI response in the database cache."""

    from .models import AIResponseCache

    AIResponseCache.objects.update_or_create(
        cache_key=key,
        defaults={
            "response_text": content,
        },
    )


# ============================================================
# GEMINI GENERATION
# ============================================================

def _generate_with_gemini(prompt, schema=None):
    """Generate content using Gemini."""

    if _gemini_client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    config = {}

    if schema is not None:
        config = {
            "response_mime_type": "application/json",
            "response_schema": schema,
        }

    response = _gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=config or None,
    )

    content = response.text

    if not content or not content.strip():
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    content = content.strip()

    # Temporary diagnostic logging.
    # Check the terminal to see whether the provider itself
    # generated malformed word spacing.
    if schema is None:
        logger.warning(
            "RAW GEMINI RESPONSE (first 2000 characters):\n%s",
            content[:2000],
        )

    return content


# ============================================================
# OLLAMA GENERATION
# ============================================================

def _generate_with_ollama(prompt, schema=None):
    """Generate content using the Ollama API."""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    if schema is not None:
        payload["format"] = schema.model_json_schema()

        payload["prompt"] += (
            "\nReturn a JSON object that strictly follows "
            "the provided schema."
        )

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=300,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    content = result.get(
        "response",
        "",
    ).strip()

    if not content:
        raise RuntimeError(
            "Ollama returned an empty response."
        )

    if schema is None:
        logger.warning(
            "RAW OLLAMA RESPONSE (first 2000 characters):\n%s",
            content[:2000],
        )

    return content


# ============================================================
# SHARED AI SERVICE
# FLOW: DATABASE CACHE -> GEMINI -> OLLAMA
# ============================================================

def generate_ai_response(
    task,
    prompt,
    schema=None,
    use_cache=True,
):
    """
    Generate text or a Pydantic-validated response.

    Flow:
        1. Check the database cache.
        2. Try Gemini.
        3. Fall back to Ollama if Gemini fails.
        4. Validate structured responses.
        5. Apply conservative cleanup to plain text.
        6. Cache successful results.
    """

    key = (
        _cache_key(task, prompt, schema)
        if use_cache
        else None
    )

    # --------------------------------------------------------
    # STEP 1: DATABASE CACHE
    # --------------------------------------------------------

    if key:
        try:
            cached = _get_cached_response(key)

            if cached:
                if schema is not None:
                    return schema.model_validate_json(cached)

                return _fix_spacing(cached)

        except Exception:
            logger.exception(
                "AI cache lookup or validation failed; "
                "continuing with generation."
            )

    # --------------------------------------------------------
    # STEP 2: GEMINI
    # --------------------------------------------------------

    try:
        content = _generate_with_gemini(
            prompt,
            schema,
        )

        if schema is not None:
            result = schema.model_validate_json(content)
        else:
            result = _fix_spacing(content)

        provider = "Gemini"

    except Exception:
        logger.exception(
            "Gemini generation or validation failed; "
            "trying Ollama."
        )

        # ----------------------------------------------------
        # STEP 3: OLLAMA FALLBACK
        # ----------------------------------------------------

        content = _generate_with_ollama(
            prompt,
            schema,
        )

        if schema is not None:
            result = schema.model_validate_json(content)
        else:
            result = _fix_spacing(content)

        provider = "Ollama"

    # --------------------------------------------------------
    # STEP 4: PREPARE RESPONSE FOR CACHING
    # --------------------------------------------------------

    if schema is not None:
        content_to_save = result.model_dump_json()
    else:
        content_to_save = result

    # --------------------------------------------------------
    # STEP 5: SAVE RESPONSE TO DATABASE CACHE
    # --------------------------------------------------------

    if key:
        try:
            _save_cached_response(
                key,
                content_to_save,
            )

        except Exception:
            logger.exception(
                "Could not save AI response to database."
            )

    logger.info(
        "AI response generated using %s.",
        provider,
    )

    return result


# ============================================================
# ADAPTIVE CONTENT GENERATION USING OLLAMA DIRECTLY
# ============================================================

def generate_with_ollama(
    topic,
    content_type,
    difficulty,
):
    """Generate adaptive-learning content using Ollama."""

    prompts = {
        "notes": (
            "Create detailed, beginner-friendly learning notes. "
            "Explain concepts step by step with examples."
        ),
        "questions": (
            "Create exactly 12 multiple-choice questions. "
            "Each must have four options, one correct answer, "
            "and a short explanation."
        ),
        "realworld": (
            "Create exactly 3 practical real-world challenges. "
            "Explain the requirements without providing "
            "complete solutions."
        ),
    }

    task_description = prompts.get(
        content_type,
        "Create useful learning material for this topic.",
    )

    prompt = f"""
You are the AI learning assistant for CognifyAI.

Topic: {topic}
Difficulty: {difficulty}
Content type: {content_type}

Task:
{task_description}

{TEXT_QUALITY_REQUIREMENTS}
"""

    content = _generate_with_ollama(prompt)

    return _fix_spacing(content)


# ============================================================
# ADAPTIVE LEARNING CONTENT: GEMINI -> OLLAMA
# ============================================================

def generate_learning_content(
    topic,
    content_type,
    difficulty,
):
    """Generate adaptive content using the shared AI service."""

    prompt = f"""
You are the AI learning assistant for CognifyAI.

Topic: {topic}
Difficulty: {difficulty}
Content type: {content_type}

Create useful, accurate learning content appropriate
for this difficulty.

For notes:
Explain concepts step by step with examples.

For questions:
Create exactly 12 MCQs with four options,
one correct answer, and an explanation for each.

For realworld:
Create exactly 3 practical challenges
without providing full solutions.

{TEXT_QUALITY_REQUIREMENTS}
"""

    try:
        content = generate_ai_response(
            task=f"adaptive_{content_type}",
            prompt=prompt,
            use_cache=True,
        )

        return content

    except Exception as exc:
        logger.exception(
            "AI generation failed for adaptive content."
        )

        raise RuntimeError(
            "Gemini and Ollama could not generate adaptive content. "
            "Check the AI service configuration and Ollama connection."
        ) from exc