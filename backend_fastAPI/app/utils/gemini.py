import json
import re
import google.generativeai as genai

from app.config import settings
from app.schemas.review_schema import AIReviewResult

genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel("gemini-3.6-flash")


PROMPT_TEMPLATE = """\
You are an expert {language} code reviewer with deep knowledge of best practices, \
security, and performance.

Analyze this {language} code carefully:

```{language}
{code}
```

Respond ONLY with a valid JSON object in this exact structure (no markdown, no extra text):
{{
  "summary": "2-3 sentence overall assessment of the code quality",
  "overall_score": <number 0-100>,
  "bugs": [
    {{
      "line": <line number or null>,
      "severity": "low|medium|high|critical",
      "category": "short general bug category, e.g. Off-by-one error, Null handling, Unhandled exception",
      "description": "what the bug is",
      "suggestion": "how to fix it"
    }}
  ],
  "security_issues": [
    {{
      "line": <line number or null>,
      "type": "e.g. SQL Injection, XSS, Hardcoded Secret",
      "description": "what the issue is",
      "fix": "how to fix it"
    }}
  ],
  "performance_issues": [
    {{
      "description": "what the performance problem is",
      "suggestion": "how to improve it",
      "impact": "low|medium|high"
    }}
  ],
  "improvements": ["tip 1", "tip 2", "tip 3"],
  "refactored_code": "the improved version of the full code",
  "complexity": {{
    "time": "O(?)",
    "space": "O(?)"
  }},
  "tags": ["relevant", "topic", "tags"]
}}
"""


async def analyze_code(code: str, language: str) -> AIReviewResult:
    """Send code to Gemini and parse the structured JSON response."""
    prompt = PROMPT_TEMPLATE.format(language=language, code=code)

    response = await _model.generate_content_async(prompt)
    text = response.text

    # Strip markdown code fences if present
    clean = re.sub(r"```json|```", "", text).strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI response was not valid JSON: {e}") from e

    return AIReviewResult(**data)


CHAT_SYSTEM_PROMPT = """\
You are a helpful code review assistant. The user is asking follow-up questions \
about the {language} code below and the review it received. Answer only from that \
context; if the question falls outside it, say so briefly.

CODE UNDER REVIEW:
```{language}
{code}
```

REVIEW SUMMARY:
{summary}
"""


async def chat_about_review(
    code: str,
    language: str,
    summary: str,
    history: list[dict],
    question: str,
) -> str:
    """Answer a follow-up question about an already-reviewed snippet.

    `history` is the prior turns as [{"role": "user"|"model", "content": str}],
    oldest first. Returns the assistant's reply text.
    """
    context = CHAT_SYSTEM_PROMPT.format(
        language=language, code=code, summary=summary or "No summary available."
    )

    # Gemini has no system role, so the context is folded into the first turn
    # and acknowledged, keeping the rest of the history strictly alternating.
    contents = [
        {"role": "user", "parts": [context]},
        {"role": "model", "parts": ["Understood. Ask me about this code."]},
    ]
    contents += [{"role": m["role"], "parts": [m["content"]]} for m in history]
    contents.append({"role": "user", "parts": [question]})

    response = await _model.generate_content_async(contents)

    text = (response.text or "").strip()
    if not text:
        raise ValueError("AI returned an empty response")
    return text
