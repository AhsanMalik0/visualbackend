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


def generate_quiz_prompt(topic: str, content: str, difficulty: str, question_count: int,
                         question_types: list[str] | None) -> str:
    types_str = ", ".join(question_types) if question_types else "multiple_choice, true_false, short_answer"

    return f"""
You are an expert educational assessment designer. Create a quiz based on the following information.

TOPIC: {topic}
DIFFICULTY: {difficulty}
NUMBER OF QUESTIONS: {question_count}
QUESTION TYPES TO USE: {types_str}

CONTENT/CONTEXT:
{content or f"General knowledge about {topic}"}

RULES:
1. Generate exactly {question_count} questions.
2. Mix question types as specified.
3. For multiple_choice: provide exactly 4 options (A, B, C, D). Only one correct answer.
4. For true_false: the answer must be "True" or "False".
5. For short_answer: the answer should be a concise phrase (1-5 words).
6. Each question must have an explanation of why the answer is correct.
7. Difficulty should match: easy = basic recall, medium = understanding/application, hard = analysis/evaluation.
8. Return ONLY a valid JSON object with no markdown, no code fences, no explanation.

OUTPUT FORMAT:
{{
  "title": "Quiz title based on topic",
  "description": "Brief quiz description",
  "questions": [
    {{
      "question_type": "multiple_choice",
      "question_text": "What is...?",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "correct_answer": "A) Option 1",
      "explanation": "Explanation of why this is correct",
      "points": 1
    }},
    {{
      "question_type": "true_false",
      "question_text": "Statement to evaluate",
      "options": ["True", "False"],
      "correct_answer": "True",
      "explanation": "Explanation",
      "points": 1
    }},
    {{
      "question_type": "short_answer",
      "question_text": "What is the term for...?",
      "options": null,
      "correct_answer": "Answer",
      "explanation": "Explanation",
      "points": 2
    }}
  ]
}}
"""


def generate_quiz(topic: str, content: str | None, difficulty: str,
                  question_count: int, question_types: list[str] | None) -> dict:
    prompt = generate_quiz_prompt(topic, content, difficulty, question_count, question_types)

    completion = client.chat.completions.create(
        model="kimi-k2-turbo-preview",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert educational assessment designer. "
                    "You output ONLY valid JSON with no markdown or code fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    raw = completion.choices[0].message.content.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw.strip())


def grade_quiz(questions: list[dict], answers: dict) -> dict:
    total_points = 0
    earned_points = 0
    corrections = {}

    for q in questions:
        q_id = str(q["id"])
        total_points += q.get("points", 1)
        user_answer = answers.get(q_id, "")

        correct = q["correct_answer"].strip().lower()
        given = str(user_answer).strip().lower()

        is_correct = correct == given

        if is_correct:
            earned_points += q.get("points", 1)

        corrections[q_id] = {
            "correct": is_correct,
            "correct_answer": q["correct_answer"],
            "user_answer": user_answer,
            "explanation": q.get("explanation", ""),
        }

    score = (earned_points / total_points * 100) if total_points > 0 else 0

    return {
        "score": round(score, 1),
        "total_points": total_points,
        "earned_points": earned_points,
        "corrections": corrections,
    }
