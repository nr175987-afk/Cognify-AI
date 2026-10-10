import json
import os
import urllib.request
import urllib.error

from .ai_generator import generate_adaptive_content


def generate_with_ollama(topic, content_type, difficulty):
    """Generate learning content using the local Ollama model."""

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
            "Create exactly 3 practical, real-world challenges. "
            "Explain each problem and its requirements, "
            "but do not provide the complete solution."
        ),
    }

    task = prompts.get(
        content_type,
        "Create useful learning material for this topic."
    )

    prompt = f"""
You are the AI learning assistant for CognifyAI.

Topic: {topic}
Difficulty: {difficulty}
Content type: {content_type}

Task:
{task}

Use clear headings and Markdown.
Match the requested difficulty.
Return only the learning content.
"""

    url = os.getenv(
        "OLLAMA_URL",
        "http://127.0.0.1:11434"
    ).rstrip("/") + "/api/generate"

    payload = {
        "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        "prompt": prompt,
        "stream": False,
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))

    content = result.get("response", "").strip()

    if not content:
        raise RuntimeError("Ollama returned empty content.")

    return content


def generate_learning_content(topic, content_type, difficulty):
    """Try Gemini first, then use Ollama if Gemini fails."""

    try:
        content = generate_adaptive_content(
            topic=topic,
            content_type=content_type,
            difficulty=difficulty,
        )

        if not content:
            raise RuntimeError("Gemini returned empty content.")

        return content

    except Exception as gemini_error:
        print(f"Gemini failed: {gemini_error}")
        print("Trying local Ollama model...")

        try:
            return generate_with_ollama(
                topic=topic,
                content_type=content_type,
                difficulty=difficulty,
            )

        except Exception as ollama_error:
            print(f"Ollama failed: {ollama_error}")

            raise RuntimeError(
                "Both Gemini and Ollama failed. "
                "Please check the AI service configuration."
            ) from ollama_error