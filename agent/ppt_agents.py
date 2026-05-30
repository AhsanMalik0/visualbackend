import os
import json
import re
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import traceback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SlideContent:
    index: int
    subtopic: str
    details: str
    learning_objective: str  # What student should understand after this slide
    interaction_type: str    # "explore", "reveal", "compare", "animate"
    checkpoint: bool         # Whether this slide has a knowledge check

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PresentationConfig:
    main_topic: str
    target_audience: str     # "students", "teachers", "executives", "general"
    complexity: str          # "introductory", "intermediate", "advanced"
    duration_minutes: int
    interaction_frequency: int  # Every N slides has active interaction
    assessment_type: str     # "none", "quiz", "discussion", "hands_on"

    def to_dict(self) -> Dict:
        return asdict(self)


class PedagogicalEngine:
    # Learning objective verbs by Bloom's taxonomy level
    BLOOM_VERBS = {
        'remember': ['identify', 'recall', 'recognize', 'list', 'name'],
        'understand': ['explain', 'describe', 'summarize', 'classify', 'compare'],
        'apply': ['demonstrate', 'implement', 'use', 'execute', 'solve'],
        'analyze': ['differentiate', 'organize', 'attribute', 'deconstruct'],
        'evaluate': ['critique', 'test', 'judge', 'justify', 'defend'],
        'create': ['design', 'construct', 'develop', 'formulate', 'author']
    }

    # 3D geometry mapping by concept type (spatial cognition research)
    CONCEPT_GEOMETRY = {
        'process': {'shape': 'helix', 'layout': 'linear', 'motion': 'flowing'},
        'hierarchy': {'shape': 'tree', 'layout': 'fractal', 'motion': 'growing'},
        'comparison': {'shape': 'dual_sphere', 'layout': 'symmetric', 'motion': 'orbiting'},
        'timeline': {'shape': 'ribbon', 'layout': 'linear', 'motion': 'weaving'},
        'network': {'shape': 'network_nodes', 'layout': 'graph', 'motion': 'pulsing'},
        'cycle': {'shape': 'torus', 'layout': 'concentric', 'motion': 'rotating'},
        'data': {'shape': 'bar_chart_3d', 'layout': 'grid', 'motion': 'scaling'},
        'concept': {'shape': 'icosahedron', 'layout': 'cluster', 'motion': 'floating'}
    }

    # Interaction types by audience (engagement research)
    AUDIENCE_INTERACTIONS = {
        'students': ['explore', 'reveal', 'quiz', 'annotate'],
        'teachers': ['compare', 'demonstrate', 'timeline', 'network'],
        'executives': ['data_viz', 'summary', 'forecast', 'decision'],
        'general': ['explore', 'reveal', 'animate']
    }

    def analyze_content(self, slides: List[Dict]) -> List[SlideContent]:
        analyzed = []

        for i, slide in enumerate(slides):
            details = slide.get('details', '')
            subtopic = slide.get('subtopic', '')

            # Determine interaction type from content analysis
            interaction = self._detect_interaction_type(details, subtopic)

            # Determine learning objective from Bloom's taxonomy
            objective = self._generate_learning_objective(subtopic, details)

            # Every 3rd slide gets a checkpoint (formative assessment)
            checkpoint = (i + 1) % 3 == 0

            analyzed.append(SlideContent(
                index=i,
                subtopic=subtopic,
                details=details,
                learning_objective=objective,
                interaction_type=interaction,
                checkpoint=checkpoint
            ))

        return analyzed

    def _detect_interaction_type(self, details: str, subtopic: str) -> str:
        """Detect optimal interaction type from content semantics"""
        text = (details + ' ' + subtopic).lower()

        if any(w in text for w in ['compare', 'versus', 'vs', 'difference', 'contrast']):
            return 'compare'
        elif any(w in text for w in ['process', 'step', 'flow', 'sequence', 'how to']):
            return 'reveal'
        elif any(w in text for w in ['data', 'statistics', 'percent', 'number', 'growth']):
            return 'explore'
        elif any(w in text for w in ['network', 'system', 'connect', 'relationship']):
            return 'explore'
        elif any(w in text for w in ['history', 'timeline', 'evolution', 'over time']):
            return 'reveal'
        else:
            return 'explore'

    def _generate_learning_objective(self, subtopic: str, details: str) -> str:
        # Simple heuristic: use "understand" + subtopic
        return f"Understand and explain {subtopic.lower()} and its significance"

    def assign_3d_scenes(self, slides: List[SlideContent]) -> List[Dict]:
        scenes = []
        used_geometries = set()

        for slide in slides:
            # Map interaction type to geometry
            concept_type = self._map_to_concept_type(slide.interaction_type, slide.subtopic)
            geo_config = self.CONCEPT_GEOMETRY.get(concept_type, self.CONCEPT_GEOMETRY['concept'])

            # Ensure uniqueness - if geometry already used, pick alternative
            base_shape = geo_config['shape']
            if base_shape in used_geometries:
                alternatives = ['icosahedron', 'torus_knot', 'octahedron', 'dodecahedron', 'mobius']
                for alt in alternatives:
                    if alt not in used_geometries:
                        base_shape = alt
                        break

            used_geometries.add(base_shape)

            # Calculate position (spaced along X axis)
            x_position = slide.index * 120  # 120 units between slides

            scenes.append({
                'slide_index': slide.index,
                'subtopic': slide.subtopic,
                'geometry': base_shape,
                'layout': geo_config['layout'],
                'motion': geo_config['motion'],
                'position': {'x': x_position, 'y': 15, 'z': 0},
                'color_primary': self._assign_color(slide.index, 'primary'),
                'color_secondary': self._assign_color(slide.index, 'secondary'),
                'interaction_type': slide.interaction_type,
                'learning_objective': slide.learning_objective,
                'checkpoint': slide.checkpoint,
                'details': slide.details
            })

        return scenes

    def _map_to_concept_type(self, interaction: str, subtopic: str) -> str:
        """Map interaction type to concept geometry category"""
        mapping = {
            'compare': 'comparison',
            'reveal': 'process',
            'explore': 'network',
            'quiz': 'data',
            'annotate': 'concept'
        }
        return mapping.get(interaction, 'concept')

    def _assign_color(self, index: int, tier: str) -> str:
        """Assign harmonious colors from cyberpunk palette"""
        palettes = [
            {'primary': '0x8b5cf6', 'secondary': '0x10b981'},  # Violet + Emerald
            {'primary': '0x06b6d4', 'secondary': '0xf59e0b'},  # Cyan + Amber
            {'primary': '0xec4899', 'secondary': '0x84cc16'},  # Pink + Lime
            {'primary': '0x6366f1', 'secondary': '0xf97316'},  # Indigo + Orange
            {'primary': '0x14b8a6', 'secondary': '0xeab308'},  # Teal + Yellow
        ]
        palette = palettes[index % len(palettes)]
        return palette[tier]


class KimiPPTClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        if not self.api_key:
            raise ValueError("KIMI_API_KEY not provided")
        self.base_url = "https://api.moonshot.ai/v1"
        self.model = "kimi-k2-turbo-preview"  # Optimized for this model
        self.total_tokens = 0

    async def _call(self, system: str, user: str, max_tokens: int = 2000, 
                    temp: float = 0.2, json_mode: bool = False) -> str:

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temp,
            "max_tokens": max_tokens
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        logger.info(f"API Call | Prompt: {len(system)+len(user)} chars | Max tokens: {max_tokens}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:

                    text = await resp.text()
                    logger.info(f"Response status: {resp.status}")

                    if resp.status != 200:
                        logger.error(f"HTTP {resp.status}: {text[:500]}")
                        raise Exception(f"HTTP {resp.status}")

                    data = json.loads(text)
                    usage = data.get("usage", {})
                    self.total_tokens += usage.get("total_tokens", 0)
                    logger.info(f"Tokens: {usage.get('prompt_tokens',0)} prompt / {usage.get('completion_tokens',0)} completion | Total used: {self.total_tokens}")

                    if "error" in data:
                        raise Exception(f"API error: {data['error']}")

                    content = data["choices"][0]["message"]["content"]
                    finish = data["choices"][0].get("finish_reason", "unknown")

                    if finish == "length":
                        logger.warning("Response TRUNCATED - increase max_tokens or reduce prompt")

                    return content

        except Exception as e:
            logger.error(f"API call failed: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            raise

    async def generate_ppt_html(self, config: PresentationConfig, 
                                 scenes: List[Dict],
                                 pedagogical_notes: str) -> str:
        system_prompt = """You are an expert Three.js developer specializing in educational 3D presentations.
Create a complete, single-file HTML interactive 3D presentation.

CRITICAL RULES:
- Output ONLY raw HTML, NO markdown code blocks, NO ```
- Use Three.js r128, GSAP 3.12, OrbitControls, Tailwind CSS (all CDN)
- Each slide is a 3D scene at unique x-coordinate (0, 120, 240, etc.)
- Include Previous/Next navigation with GSAP camera animation
- Dark cyberpunk theme: bg #050510, accents violet #8b5cf6 and emerald #10b981
- Responsive design with UI overlay for slide content
- Start with <!DOCTYPE html>, end with </html>
- Add keyboard navigation (arrow keys) and slide counter"""

        # CONDENSED scene summary (not full dump)
        scene_summary = []
        for s in scenes:
            scene_summary.append({
                'index': s['slide_index'],
                'title': s['subtopic'],
                'geometry': s['geometry'],
                'position': s['position'],
                'colors': [s['color_primary'], s['color_secondary']],
                'interaction': s['interaction_type']
            })

        user_prompt = f"""Create a 3D Interactive Presentation HTML file.

TOPIC: {config.main_topic}
AUDIENCE: {config.target_audience}
COMPLEXITY: {config.complexity}

SLIDE SCENES (condensed):
{json.dumps(scene_summary, indent=2)}

PEDAGOGICAL DESIGN:
{pedagogical_notes}

REQUIREMENTS:
1. Each slide scene at x = index * 120, with unique 3D geometry
2. GSAP camera transition (duration 1.2s, power2.inOut) between slides
3. UI overlay: dark panel (rgba(0,0,0,0.55), backdrop-filter blur) showing current slide content
4. Navigation: Prev/Next buttons bottom-center, slide counter, keyboard arrows
5. Text fade out/in during transitions
6. Main topic header top-left persistent
7. Floating particles and ambient glow per scene
8. Mobile-responsive

Generate the COMPLETE HTML now."""

        try:
            html = await self._call(system_prompt, user_prompt, max_tokens=2500, temp=0.15)

            # Clean markdown if present
            html = re.sub(r'^```html\s*', '', html, flags=re.MULTILINE)
            html = re.sub(r'^```\s*', '', html, flags=re.MULTILINE)
            html = re.sub(r'```\s*$', '', html, flags=re.MULTILINE)
            html = html.strip()

            # Validate
            if '<!DOCTYPE html>' not in html and '<html' not in html:
                match = re.search(r'(<[?!]?html.*?</html>)', html, re.DOTALL | re.IGNORECASE)
                if match:
                    html = match.group(1)
                else:
                    raise Exception("No valid HTML in response")

            logger.info(f"Generated HTML: {len(html)} chars")
            return html

        except Exception as e:
            logger.error(f"HTML generation failed: {e}")
            return self._fallback_template(config, scenes)

    def _fallback_template(self, config: PresentationConfig, scenes: List[Dict]) -> str:
        # Build slide data JS
        slides_js = []
        for s in scenes:
            slides_js.append(f"""
    {{
        title: "{s['subtopic'].replace('"', '\\"')}",
        details: "{s['details'][:100].replace('"', '\\"')}...",
        position: {{ x: {s['position']['x']}, y: {s['position']['y']}, z: {s['position']['z']} }},
        color: {s['color_primary']},
        geometry: "{s['geometry']}"
    }}""")

        slides_array = ",".join(slides_js)
        total_slides = len(scenes)

        # Geometry generators
        geo_generators = {
            'helix': 'new THREE.TorusKnotGeometry(8, 2, 100, 16)',
            'tree': 'new THREE.ConeGeometry(6, 15, 8)',
            'dual_sphere': 'new THREE.IcosahedronGeometry(7, 1)',
            'ribbon': 'new THREE.TorusGeometry(8, 2, 16, 100)',
            'network_nodes': 'new THREE.OctahedronGeometry(6, 0)',
            'torus': 'new THREE.TorusGeometry(8, 3, 16, 100)',
            'bar_chart_3d': 'new THREE.BoxGeometry(4, 10, 4)',
            'icosahedron': 'new THREE.IcosahedronGeometry(7, 2)',
            'torus_knot': 'new THREE.TorusKnotGeometry(7, 2, 100, 16)',
            'octahedron': 'new THREE.OctahedronGeometry(7, 0)',
            'dodecahedron': 'new THREE.DodecahedronGeometry(7, 0)',
            'mobius': 'new THREE.TorusKnotGeometry(7, 2, 100, 16)'
        }

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.main_topic} - 3D Presentation</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
    <style>
        body {{ margin: 0; overflow: hidden; background: #050510; font-family: system-ui, sans-serif; }}
        #canvas-container {{ width: 100vw; height: 100vh; position: fixed; top: 0; left: 0; }}
        .ui-overlay {{ pointer-events: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 10; }}
        .slide-panel {{
            position: absolute; right: 40px; top: 50%; transform: translateY(-50%);
            width: 380px; max-height: 70vh; overflow-y: auto;
            background: rgba(0,0,0,0.55); backdrop-filter: blur(20px);
            border: 1px solid rgba(139,92,246,0.3); border-radius: 16px;
            padding: 28px; color: white;
            opacity: 0; transition: opacity 0.5s ease;
        }}
        .slide-panel.active {{ opacity: 1; }}
        .nav-bar {{
            position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%);
            display: flex; align-items: center; gap: 20px;
            background: rgba(0,0,0,0.6); backdrop-filter: blur(10px);
            padding: 12px 28px; border-radius: 50px;
            border: 1px solid rgba(139,92,246,0.3); z-index: 20;
        }}
        .nav-btn {{
            background: linear-gradient(135deg, #8b5cf6, #10b981);
            border: none; color: white; padding: 10px 24px;
            border-radius: 25px; cursor: pointer; font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
            pointer-events: auto;
        }}
        .nav-btn:hover {{ transform: scale(1.05); box-shadow: 0 0 20px rgba(139,92,246,0.5); }}
        .nav-btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}
        .counter {{ color: #a78bfa; font-weight: 700; font-size: 14px; min-width: 50px; text-align: center; }}
        .topic-header {{
            position: fixed; top: 24px; left: 24px; z-index: 20;
            color: #8b5cf6; font-size: 12px; font-weight: 700;
            letter-spacing: 3px; text-transform: uppercase;
            background: rgba(0,0,0,0.4); padding: 8px 16px;
            border-radius: 20px; border: 1px solid rgba(139,92,246,0.3);
        }}
        .progress-bar {{
            position: fixed; bottom: 0; left: 0; height: 3px;
            background: linear-gradient(90deg, #8b5cf6, #10b981);
            transition: width 0.8s ease; z-index: 30;
        }}
        .checkpoint-badge {{
            display: inline-block; background: #10b981; color: #050510;
            padding: 4px 12px; border-radius: 12px; font-size: 11px;
            font-weight: 700; margin-top: 12px;
        }}
    </style>
</head>
<body>
    <div id="canvas-container"></div>

    <div class="topic-header">{config.main_topic}</div>

    <div class="ui-overlay">
        <div class="slide-panel" id="slidePanel">
            <h2 id="slideTitle" class="text-2xl font-bold mb-3 text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-emerald-400"></h2>
            <p id="slideDetails" class="text-gray-300 text-sm leading-relaxed"></p>
            <div id="checkpointBadge"></div>
        </div>
    </div>

    <div class="nav-bar">
        <button class="nav-btn" id="prevBtn" onclick="goToSlide(currentSlide - 1)">Previous</button>
        <span class="counter" id="slideCounter">1 / {total_slides}</span>
        <button class="nav-btn" id="nextBtn" onclick="goToSlide(currentSlide + 1)">Next</button>
    </div>

    <div class="progress-bar" id="progressBar" style="width: 0%"></div>

    <script>
        const SLIDES = [{slides_array}];
        let currentSlide = 0;
        const TOTAL_SLIDES = SLIDES.length;

        // Scene setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x050510);
        scene.fog = new THREE.FogExp2(0x050510, 0.003);

        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
        camera.position.set(0, 20, 80);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.toneMapping = THREE.ReinhardToneMapping;
        document.getElementById('canvas-container').appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.minDistance = 30;
        controls.maxDistance = 150;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.8);
        scene.add(ambientLight);

        // Create slide scenes
        const slideGroups = [];
        const geoMap = {{
            'helix': new THREE.TorusKnotGeometry(8, 2, 100, 16),
            'tree': new THREE.ConeGeometry(6, 15, 8),
            'dual_sphere': new THREE.IcosahedronGeometry(7, 1),
            'ribbon': new THREE.TorusGeometry(8, 2, 16, 100),
            'network_nodes': new THREE.OctahedronGeometry(6, 0),
            'torus': new THREE.TorusGeometry(8, 3, 16, 100),
            'bar_chart_3d': new THREE.BoxGeometry(4, 10, 4),
            'icosahedron': new THREE.IcosahedronGeometry(7, 2),
            'torus_knot': new THREE.TorusKnotGeometry(7, 2, 100, 16),
            'octahedron': new THREE.OctahedronGeometry(7, 0),
            'dodecahedron': new THREE.DodecahedronGeometry(7, 0),
            'mobius': new THREE.TorusKnotGeometry(7, 2, 100, 16)
        }};

        SLIDES.forEach((slide, idx) => {{
            const group = new THREE.Group();
            group.position.set(slide.position.x, slide.position.y, slide.position.z);

            // Main geometry
            const geo = geoMap[slide.geometry] || geoMap['icosahedron'];
            const mat = new THREE.MeshPhysicalMaterial({{
                color: slide.color,
                metalness: 0.3,
                roughness: 0.2,
                transmission: 0.4,
                transparent: true,
                emissive: slide.color,
                emissiveIntensity: 0.15
            }});
            const mesh = new THREE.Mesh(geo, mat);
            group.add(mesh);

            // Orbiting particles
            const pGeo = new THREE.BufferGeometry();
            const pCount = 200;
            const pPos = new Float32Array(pCount * 3);
            for (let i = 0; i < pCount; i++) {{
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.random() * Math.PI;
                const r = 15 + Math.random() * 10;
                pPos[i*3] = r * Math.sin(phi) * Math.cos(theta);
                pPos[i*3+1] = r * Math.sin(phi) * Math.sin(theta);
                pPos[i*3+2] = r * Math.cos(phi);
            }}
            pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
            const pMat = new THREE.PointsMaterial({{
                color: 0x10b981, size: 0.3, transparent: true, opacity: 0.6,
                blending: THREE.AdditiveBlending
            }});
            group.add(new THREE.Points(pGeo, pMat));

            // Point light
            const pl = new THREE.PointLight(slide.color, 1.5, 100);
            pl.position.set(0, 10, 0);
            group.add(pl);

            scene.add(group);
            slideGroups.push(group);
        }});

        // Update UI
        function updateUI() {{
            const panel = document.getElementById('slidePanel');
            panel.classList.remove('active');

            setTimeout(() => {{
                const slide = SLIDES[currentSlide];
                document.getElementById('slideTitle').textContent = slide.title;
                document.getElementById('slideDetails').textContent = slide.details;
                document.getElementById('slideCounter').textContent = `${{currentSlide + 1}} / ${{TOTAL_SLIDES}}`;
                document.getElementById('progressBar').style.width = `${{((currentSlide + 1) / TOTAL_SLIDES) * 100}}%`;

                const badge = document.getElementById('checkpointBadge');
                if ((currentSlide + 1) % 3 === 0) {{
                    badge.innerHTML = '<span class="checkpoint-badge">Knowledge Check</span>';
                }} else {{
                    badge.innerHTML = '';
                }}

                document.getElementById('prevBtn').disabled = currentSlide === 0;
                document.getElementById('nextBtn').disabled = currentSlide === TOTAL_SLIDES - 1;

                panel.classList.add('active');
            }}, 500);
        }}

        // Navigation
        function goToSlide(index) {{
            if (index < 0 || index >= TOTAL_SLIDES) return;

            currentSlide = index;
            const target = SLIDES[index].position;

            gsap.to(camera.position, {{
                x: target.x,
                y: target.y + 20,
                z: 80,
                duration: 1.2,
                ease: "power2.inOut"
            }});

            gsap.to(controls.target, {{
                x: target.x,
                y: target.y,
                z: target.z,
                duration: 1.2,
                ease: "power2.inOut",
                onUpdate: () => controls.update()
            }});

            updateUI();
        }}

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ') goToSlide(currentSlide + 1);
            if (e.key === 'ArrowLeft') goToSlide(currentSlide - 1);
        }});

        // Animation loop
        const clock = new THREE.Clock();
        function animate() {{
            requestAnimationFrame(animate);
            const time = clock.getElapsedTime();

            slideGroups.forEach((group, idx) => {{
                group.rotation.y = time * 0.2 + idx;
                group.rotation.x = Math.sin(time * 0.5 + idx) * 0.1;
                group.position.y = SLIDES[idx].position.y + Math.sin(time + idx) * 2;
            }});

            controls.update();
            renderer.render(scene, camera);
        }}

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});

        // Initialize
        updateUI();
        animate();
    </script>
</body>
</html>"""


class SlideVerseAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.kimi = KimiPPTClient(api_key)
        self.pedagogy = PedagogicalEngine()

    async def generate(self, main_topic: str, slides: List[Dict],
                       target_audience: str = "students",
                       complexity: str = "intermediate") -> Dict[str, Any]:

        logger.info(f"=== SlideVerse Generation: {main_topic} ===")
        start = datetime.now()

        # Step 1: Configure presentation
        config = PresentationConfig(
            main_topic=main_topic,
            target_audience=target_audience,
            complexity=complexity,
            duration_minutes=len(slides) * 3,
            interaction_frequency=3,
            assessment_type="quiz" if target_audience == "students" else "discussion"
        )

        # Step 2: Pedagogical analysis
        logger.info("Analyzing content pedagogically...")
        analyzed_slides = self.pedagogy.analyze_content(slides)

        # Step 3: Assign 3D scenes
        logger.info("Assigning 3D scenes...")
        scenes = self.pedagogy.assign_3d_scenes(analyzed_slides)

        # Step 4: Build pedagogical notes for prompt
        ped_notes = self._build_pedagogical_notes(analyzed_slides, config)

        # Step 5: Generate HTML via Kimi
        logger.info("Generating 3D HTML presentation...")
        try:
            html = await self.kimi.generate_ppt_html(config, scenes, ped_notes)
            source = 'api' if not html.startswith('<!-- Fallback') else 'fallback'
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            html = self.kimi._fallback_template(config, scenes)
            source = 'fallback'

        duration = (datetime.now() - start).total_seconds()

        result = {
            'metadata': {
                'topic': main_topic,
                'slides_count': len(slides),
                'generation_time': duration,
                'tokens_used': self.kimi.total_tokens,
                'source': source,
                'timestamp': datetime.now().isoformat()
            },
            'config': config.to_dict(),
            'scenes': scenes,
            'slides': [s.to_dict() for s in analyzed_slides],
            'html': html,
            'filename': f"{main_topic.lower().replace(' ', '_')}_3d_ppt.html"
        }

        logger.info(f"Complete: {duration:.1f}s | Source: {source} | Tokens: {self.kimi.total_tokens}")
        return result

    def _build_pedagogical_notes(self, slides: List[SlideContent], config: PresentationConfig) -> str:
        notes = []
        notes.append(f"Audience: {config.target_audience} | Complexity: {config.complexity}")
        notes.append(f"Interaction pattern: Every {config.interaction_frequency} slides")

        for s in slides:
            checkpoint = " [CHECKPOINT]" if s.checkpoint else ""
            notes.append(f"Slide {s.index+1}: {s.interaction_type} interaction{checkpoint} | Objective: {s.learning_objective}")

        return "\n".join(notes)

    def save(self, result: Dict, output_dir: str = "./3Dpresentations") -> str:
        """Save generated presentation"""
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, result['filename'])
        with open(path, 'w', encoding='utf-8') as f:
            f.write(result['html'])
        logger.info(f"Saved: {path}")
        return path


# ============== USAGE EXAMPLES ==============

async def demo():
    agent = SlideVerseAgent(api_key="YOUR_API_KEY_HERE")

    slides = [
        {
            "subtopic": "Introduction to Neural Networks",
            "details": "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) that process information in layers."
        },
        {
            "subtopic": "The Perceptron",
            "details": "The perceptron is the simplest neural network unit. It takes multiple inputs, applies weights, sums them, and passes through an activation function to produce output."
        },
        {
            "subtopic": "Multi-Layer Architecture",
            "details": "Deep neural networks have input layers, hidden layers, and output layers. Each layer extracts increasingly abstract features from the input data."
        },
        {
            "subtopic": "Backpropagation",
            "details": "Backpropagation is the algorithm used to train neural networks. It calculates gradients of the loss function with respect to weights and updates them to minimize error."
        },
        {
            "subtopic": "Modern Applications",
            "details": "Today, neural networks power image recognition, natural language processing, autonomous vehicles, medical diagnosis, and generative AI systems."
        }
    ]

    result = await agent.generate(
        main_topic="Neural Networks Explained",
        slides=slides,
        target_audience="students",
        complexity="intermediate"
    )

    print(f"\\n{'='*60}")
    print(f"3D PPT Generated: {result['metadata']['topic']}")
    print(f"Source: {result['metadata']['source']}")
    print(f"HTML size: {len(result['html'])} chars")
    print(f"Tokens used: {result['metadata']['tokens_used']}")
    print(f"Time: {result['metadata']['generation_time']:.1f}s")

    agent.save(result)
    return result


async def custom_generate(main_topic: str, slides_data: List[Dict], 
                          audience: str = "students", api_key: Optional[str] = None):
    key = api_key or os.getenv("KIMI_API_KEY")
    agent = SlideVerseAgent(api_key=key)

    result = await agent.generate(
        main_topic=main_topic,
        slides=slides_data,
        target_audience=audience
    )

    path = agent.save(result)
    print(f"\\nSaved 3D presentation: {path}")
    print(f"Open in browser to view interactive presentation")
    return result


# if __name__ == "__main__":
#     # Run demo
#     asyncio.run(demo())