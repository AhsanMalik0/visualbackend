import json
import re
from openai import OpenAI
from google import genai
from google.genai import types

from utils.config import GEMINI_API_KEY, KIMI_API_KEY

Gemini_client = genai.Client(api_key=GEMINI_API_KEY)

client = OpenAI(
    api_key=KIMI_API_KEY,
    base_url="https://api.moonshot.ai/v1",
)


SUMMARY_LENGTH = {
    "brief": "2-3 sentences maximum. Ultra-concise.",
    "standard": "1-2 paragraphs. Cover main points clearly.",
    "detailed": "3-5 paragraphs. Comprehensive with examples and context.",
}


def summarize_content(title: str, content: str, summary_type: str = "standard",
                      language: str = "english") -> dict:
    length_instruction = SUMMARY_LENGTH.get(summary_type, SUMMARY_LENGTH["standard"])

    prompt = f"""
You are an expert academic summarizer. Summarize the following content.

TITLE: {title}
SUMMARY LENGTH: {summary_type} - {length_instruction}
LANGUAGE: {language}

CONTENT TO SUMMARIZE:
{content}

RULES:
1. Create a clear, accurate summary at the specified length.
2. Extract 3-7 key points as bullet points.
3. Maintain academic accuracy - do not add information not in the original.
4. If language is not English, translate the summary to the specified language.
5. Return ONLY a valid JSON object with no markdown, no code fences.

OUTPUT FORMAT:
{{
  "summary": "The summarized text here...",
  "key_points": [
    "Key point 1",
    "Key point 2",
    "Key point 3"
  ],
  "word_count_original": <number>,
  "word_count_summary": <number>
}}
"""

    completion = client.chat.completions.create(
        model="kimi-k2-turbo-preview",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert academic summarizer. "
                    "You output ONLY valid JSON with no markdown or code fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )

    raw = completion.choices[0].message.content.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw.strip())


def customize_lecture(topic: str, content: str, customization_type: str,
                      target_audience: str | None = None,
                      language: str = "english",
                      additional_instructions: str | None = None) -> dict:
    customization_map = {
        "simplify": "Simplify the language and concepts for easier understanding. Use simpler vocabulary and shorter sentences.",
        "detailed": "Expand on each point with more depth, examples, and context. Add supporting details.",
        "visual_heavy": "Restructure the content to emphasize visual descriptions. Suggest diagrams, charts, and 3D models for each concept.",
        "interactive": "Add interactive elements: discussion questions, activities, hands-on exercises, and group work suggestions.",
        "age_appropriate": f"Adapt the content for {target_audience or 'general'} audience. Adjust vocabulary, examples, and complexity.",
    }

    customization_instruction = customization_map.get(
        customization_type,
        f"Customize according to: {customization_type}"
    )

    prompt = f"""
You are an expert educational content designer. Customize the following lecture content.

TOPIC: {topic}
CUSTOMIZATION: {customization_type} - {customization_instruction}
TARGET AUDIENCE: {target_audience or "General"}
LANGUAGE: {language}
{f"ADDITIONAL INSTRUCTIONS: {additional_instructions}" if additional_instructions else ""}

ORIGINAL CONTENT:
{content}

RULES:
1. Apply the customization while preserving all key information.
2. Maintain academic accuracy.
3. Structure the output clearly with sections.
4. If language is not English, provide the customized content in the specified language.
5. Return ONLY a valid JSON object with no markdown, no code fences.

OUTPUT FORMAT:
{{
  "customized_title": "Updated title",
  "customized_content": "The fully customized lecture content...",
  "sections": [
    {{
      "heading": "Section 1 Title",
      "content": "Section content...",
      "visual_suggestions": ["Suggested visual 1"],
      "activities": ["Suggested activity 1"]
    }}
  ],
  "key_changes": ["What was changed and why"],
  "visual_recommendations": ["Recommended 3D models or visuals to generate"]
}}
"""

    completion = client.chat.completions.create(
        model="kimi-k2-turbo-preview",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert educational content designer. "
                    "You output ONLY valid JSON with no markdown or code fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
    )

    raw = completion.choices[0].message.content.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw.strip())
