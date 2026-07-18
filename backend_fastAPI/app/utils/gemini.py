import json
import re
import google.generativeai as genai

from app.config import settings
from app.schemas.review_schema import AIReviewResult

genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel("gemini-3.5-flash")


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
