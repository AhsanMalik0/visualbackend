import json
import re
from openai import OpenAI
from google import genai
from google.genai import types

from schemas.schemas import GeneratePlanRequest
from utils.config import GEMINI_API_KEY, KIMI_API_KEY

# Initialize API clients
Gemini_client = genai.Client(api_key=GEMINI_API_KEY)

client = OpenAI(
    api_key=KIMI_API_KEY,
    base_url="https://api.moonshot.ai/v1",
)


def build_plan_prompt(data: GeneratePlanRequest) -> str:
    book_info = f'the book "{data.book_name}"' if data.book_name else "relevant academic sources"

    return f"""
You are an expert curriculum designer. 
TASK: Use your knowledge of {book_info} to create a comprehensive lecture plan.

COURSE DETAILS:
- Class Name: {data.class_name}
- Subject: {data.subject}
- Focus/Outline: {data.outline}
- Total Lectures: {data.total_lectures}
- Target Audience: {data.age_min}-{data.age_max} years old ({data.education_level})

OUTPUT FORMAT:
Return ONLY a valid JSON array of {data.total_lectures} objects. 
No markdown, no explanation, no backticks (```), no code fences.

[
  {{
    "lecture_number": 1,
    "title": "Specific Title",
    "description": "In-depth description...",
    "key_points": ["Point 1", "Point 2"],
    "examples": ["Relevant Example"],
    "activities": ["Interactive Activity"],
    "duration_minutes": {int(data.hours_per_lecture * 60)}
  }}
]
"""


def generate_prompt(book_title, book_content, blueprint):
    prompt = f"""
You are an expert Three.js developer creating a museum-quality 3D visualization.

TITLE: "{book_title}"

VISUAL BLUEPRINT (follow this precisely):
- Core Concept: {blueprint['core_concept']}
- Visual Metaphor: {blueprint['visual_metaphor']}
- Primary Geometry: {blueprint['geometry']['primary_shape']}
- Secondary Elements: {', '.join(blueprint['geometry']['secondary_shapes'])}
- Animation Style: {blueprint['geometry']['animation_style']}
- Primary Color: {blueprint['color_palette']['primary']}
- Secondary Color: {blueprint['color_palette']['secondary']}
- Accent Color: {blueprint['color_palette']['accent']}
- Background: {blueprint['color_palette']['background']}

KEY OBJECTS TO BUILD:
{chr(10).join([f"  - {obj['name']}: {obj['shape']} at {obj['position']} — represents {obj['meaning']}" for obj in blueprint['key_objects']])}

DATA ENCODING RULES:
{chr(10).join([f"  - {enc}" for enc in blueprint['data_encoding']])}

INTERACTIVE ELEMENTS:
{chr(10).join([f"  - {el}" for el in blueprint['interactive_elements']])}

AVOID: {', '.join(blueprint['avoid'])}

TECHNICAL REQUIREMENTS:
- Use Three.js r128 (CDN), GSAP (CDN), OrbitControls
- Dark background: {blueprint['color_palette']['background']}
- Responsive canvas that fills the viewport
- Add an HTML overlay panel (top-left) showing "{book_title}" and a 1-line description
- Camera starts at a dramatic angle, auto-rotates slowly
- On mouse hover over key objects: show a tooltip with their meaning
- Smooth 60fps animation loop
- All geometry must clearly express the blueprint metaphor above — not generic shapes

OUTPUT: ONLY the code, starting with <!DOCTYPE html> and ending with </html>.
"""
    return prompt


def visualization_prompt(book_title, book_content):
    gemini_prompt = f"""
You are a creative director specializing in 3D data visualization. 
Analyze this text and produce a STRICT JSON visual specification.

BOOK/TEXT: "{book_content}"

Respond ONLY with a JSON object. No markdown, no preamble.

{{
  "core_concept": "1-sentence essence of what this text is about",
  "visual_metaphor": "the primary 3D metaphor (e.g. 'neural network as a glowing city', 'grief as ocean depth', 'evolution as branching tree')",
  "geometry": {{
    "primary_shape": "the dominant 3D object type (e.g. 'particles', 'spiral', 'network graph', 'terrain', 'crystalline lattice', 'flowing ribbons')",
    "secondary_shapes": ["list", "of", "supporting", "elements"],
    "animation_style": "how it moves (e.g. 'pulsing', 'orbiting', 'flowing', 'exploding outward', 'breathing')"
  }},
  "color_palette": {{
    "primary": "#hexcode",
    "secondary": "#hexcode",
    "accent": "#hexcode",
    "background": "#hexcode",
    "mood": "why these colors match the theme"
  }},
  "data_encoding": [
    "how specific concepts map to visual properties",
    "e.g. 'intensity of conflict = particle speed'",
    "e.g. 'chapter progression = z-axis depth'"
  ],
  "interactive_elements": [
    "what the user can click/drag/hover to reveal meaning",
    "e.g. 'hover node reveals character name'"
  ],
  "key_objects": [
    {{"name": "object name", "shape": "geometry type", "meaning": "what it represents", "position": "where in 3D space"}}
  ],
  "avoid": ["visual clichés to avoid for this specific topic"],
  "technical_hints": ["specific Three.js techniques that suit this visualization"]
}}
"""
    response = Gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=gemini_prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low")
        ),
    )
    blueprints = json.loads(response.text)
    prompt = generate_prompt(book_title=book_title, book_content=book_content, blueprint=blueprints)
    return prompt


def plan_generate(final_prompt):
    completion = client.chat.completions.create(
        model="kimi-k2-turbo-preview",
        messages=[
            {"role": "system", "content": "You are a professional curriculum assistant. You only output valid JSON arrays."},
            {"role": "user", "content": final_prompt},
        ],
        temperature=0.3,
    )
    raw = completion.choices[0].message.content.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw.strip())


def ppt_prompt(main_topic: str, slides: list[dict]) -> str:
    slides_text = ""
    for i, slide in enumerate(slides):
        slides_text += f"""
SLIDE {i+1}:
- Subtopic: {slide['subtopic']}
- Details: {slide['details']}
"""

    return f"""
You are an expert 3D web developer. Create a professional 3D Interactive Presentation as a SINGLE self-contained HTML file.

MAIN TOPIC: {main_topic}
CONTENT STRUCTURE:
{slides_text}

TECHNICAL SPECIFICATIONS:
1. LIBRARIES: Three.js r128 (https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js), GSAP 3 (https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js), OrbitControls (https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js). All via CDN.

2. 3D LAYOUT:
   - Place each slide's 3D scene at a DIFFERENT x-coordinate: Slide 1 at x=0, Slide 2 at x=100, Slide 3 at x=200, etc.
   - Each slide must have a UNIQUE 3D geometry representing its subtopic.
   - Add floating particles and ambient glow to each slide's scene.

3. NAVIGATION:
   - Previous / Next buttons fixed at bottom center.
   - On click, use GSAP to smoothly animate BOTH camera.position AND OrbitControls.target to the next slide's coordinates (duration 1.2s, ease power2.inOut).
   - Show a slide counter (e.g. "2 / 5") between the buttons.

4. UI OVERLAY:
   - A transparent dark panel (rgba(0,0,0,0.55), backdrop-filter blur) shows the current slide's subtopic and details.
   - Text fades out before transition and fades in after.
   - Main topic shown as small header top-left at all times.

5. THEME:
   - Background: #050510
   - Accent colors: violet (#8b5cf6) and emerald (#10b981)
   - Font: system-ui or sans-serif, white text
   - Futuristic cyberpunk aesthetic

6. OUTPUT: Return ONLY the raw HTML starting with <!DOCTYPE html> and ending with </html>. No markdown, no code fences, no explanation.
"""


def split_slides_prompt(main_topic: str, raw_content: str) -> str:
    return f"""
You are a presentation expert. Split the following content into structured slides for a 3D presentation.

MAIN TOPIC: {main_topic}
RAW CONTENT:
{raw_content}

RULES:
- Create between 3 and 8 slides.
- Each slide should cover one clear subtopic.
- Keep details concise (2-3 sentences max per slide).
- Return ONLY a valid JSON array, no markdown, no explanation.

FORMAT:
[
  {{"subtopic": "Slide title here", "details": "2-3 sentence description here"}},
  {{"subtopic": "Next slide title", "details": "Description here"}}
]
"""


def edit_prompt(original_html: str, edit_instructions: str) -> str:
    return f"""
You are an expert 3D web developer. Modify the following HTML visualization based on the instructions below.

EDIT INSTRUCTIONS:
{edit_instructions}

ORIGINAL HTML:
{original_html}

RULES:
- Apply ONLY the requested changes. Keep everything else exactly the same.
- If changing colors, update ALL related elements consistently.
- If editing text, preserve all HTML structure around it.
- If changing animation style, update the GSAP/Three.js code accordingly.
- Return ONLY the complete modified HTML starting with <!DOCTYPE html> and ending with </html>. No markdown, no explanation.
"""


def generate(prompt: str) -> str:
    completion = client.chat.completions.create(
        model="kimi-k2-turbo-preview",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a world-class 3D Creative Technologist and Three.js expert. "
                    "You output ONLY raw, production-ready HTML starting with <!DOCTYPE html> "
                    "and ending with </html>. No markdown, no code fences, no explanation."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
    )

    raw = completion.choices[0].message.content.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    return raw


def split_slides_with_ai(main_topic: str, raw_content: str) -> list[dict]:
    prompt = split_slides_prompt(main_topic, raw_content)
    response = generate(prompt)
    try:
        slides = json.loads(response)
        return slides
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("AI failed to return valid slide JSON")
