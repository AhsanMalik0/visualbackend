import os
import json
import re
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VisualStyle(Enum):
    CYBERPUNK = "cyberpunk"
    ETHEREAL = "ethereal"
    INDUSTRIAL = "industrial"
    ORGANIC = "organic"
    MINIMAL = "minimal"
    BIO_TECH = "bio_tech"
    COSMIC = "cosmic"
    AQUATIC = "aquatic"


@dataclass
class ExtractedConcepts:
    topic: str
    materials: List[str]
    shapes: List[str]
    colors: List[str]
    atmosphere: List[str]
    animations: List[str]
    layout: str
    lighting: str
    mood: str
    scale: str  # intimate, grand, vast
    temporal: str  # static, dynamic, chaotic
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TechnicalSpec:
    fog_density: float
    camera_position: Tuple[float, float, float]
    particle_count: int
    shadow_map_size: int
    antialias: bool
    tone_mapping: str
    post_processing: List[str]


class ConceptDatabase:
    
    MATERIALS = {
        'obsidian': {'color': '0x111116', 'roughness': 0.2, 'metalness': 0.8, 'type': 'standard'},
        'crystal': {'color': '0xa8a8b3', 'roughness': 0.0, 'metalness': 0.1, 'transmission': 0.9, 'transparent': True, 'type': 'physical'},
        'glass': {'color': '0xffffff', 'roughness': 0.0, 'transmission': 0.95, 'transparent': True, 'type': 'physical'},
        'neon': {'emissive': True, 'roughness': 0.4, 'type': 'standard'},
        'steel': {'color': '0x4a5568', 'roughness': 0.3, 'metalness': 0.9, 'type': 'standard'},
        'gold': {'color': '0xffd700', 'roughness': 0.2, 'metalness': 1.0, 'type': 'standard'},
        'organic': {'color': '0x2d6a4f', 'roughness': 0.8, 'type': 'standard'},
        'bioluminescent': {'color': '0x00ff88', 'emissive': '0x00ff88', 'emissiveIntensity': 0.5, 'type': 'standard'},
        'holographic': {'color': '0x00ffff', 'transmission': 0.7, 'opacity': 0.3, 'transparent': True, 'type': 'physical'},
        'rusted': {'color': '0x8b4513', 'roughness': 0.9, 'metalness': 0.4, 'type': 'standard'},
        'ice': {'color': '0xe0f7fa', 'roughness': 0.1, 'transmission': 0.8, 'transparent': True, 'type': 'physical'},
        'marble': {'color': '0xf5f5f5', 'roughness': 0.1, 'metalness': 0.1, 'type': 'standard'},
        'chrome': {'color': '0xc0c0c0', 'roughness': 0.0, 'metalness': 1.0, 'type': 'standard'},
    }
    
    SHAPES = {
        'tower': {'geometry': 'BoxGeometry', 'params': [2, 10, 2], 'pivot': 'bottom'},
        'spire': {'geometry': 'CylinderGeometry', 'params': [0.5, 2, 15, 8], 'pivot': 'bottom'},
        'sphere': {'geometry': 'IcosahedronGeometry', 'params': [3, 2], 'pivot': 'center'},
        'dome': {'geometry': 'SphereGeometry', 'params': [5, 32, 16, 0, 'Math.PI * 2', 0, 'Math.PI / 2'], 'pivot': 'bottom'},
        'ring': {'geometry': 'TorusGeometry', 'params': [5, 0.5, 16, 100], 'pivot': 'center'},
        'arch': {'geometry': 'TorusGeometry', 'params': [3, 0.3, 16, 50, 'Math.PI'], 'pivot': 'center'},
        'crystal': {'geometry': 'OctahedronGeometry', 'params': [2, 0], 'pivot': 'center'},
        'tree': {'geometry': 'ConeGeometry', 'params': [3, 10, 8], 'pivot': 'bottom'},
        'platform': {'geometry': 'CylinderGeometry', 'params': [8, 8, 1, 32], 'pivot': 'bottom'},
        'ribbon': {'geometry': 'TubeGeometry', 'curve': True, 'params': [64, 0.5, 8, False], 'pivot': 'center'},
        'monolith': {'geometry': 'BoxGeometry', 'params': [4, 20, 4], 'pivot': 'bottom'},
        'shard': {'geometry': 'ConeGeometry', 'params': [1, 8, 4], 'pivot': 'bottom'},
        'orb': {'geometry': 'SphereGeometry', 'params': [3, 64, 64], 'pivot': 'center'},
        'helix': {'geometry': 'custom', 'generator': 'generate_helix_curve', 'pivot': 'center'},
    }
    
    COLORS = {
        'violet': '0x8b5cf6', 'purple': '0x8b5cf6', 'magenta': '0xd946ef',
        'emerald': '0x10b981', 'green': '0x10b981', 'lime': '0x84cc16',
        'cyan': '0x06b6d4', 'blue': '0x3b82f6', 'azure': '0x0ea5e9',
        'rose': '0xf43f5e', 'red': '0xef4444', 'orange': '0xf97316',
        'amber': '0xf59e0b', 'yellow': '0xeab308', 'gold': '0xfcd34d',
        'white': '0xffffff', 'silver': '0xc0c0c0', 'black': '0x000000',
        'pink': '0xec4899', 'indigo': '0x6366f1', 'teal': '0x14b8a6',
        'crimson': '0xdc2626', 'lavender': '0xa78bfa', 'mint': '0x6ee7b7',
    }
    
    ATMOSPHERE = {
        'rain': {'type': 'particles', 'count': 1500, 'color': 'emerald', 'motion': 'downward', 'speed': 0.5, 'size': 0.2},
        'snow': {'type': 'particles', 'count': 1000, 'color': 'white', 'motion': 'drift', 'speed': 0.2, 'size': 0.3},
        'embers': {'type': 'particles', 'count': 800, 'color': 'orange', 'motion': 'upward', 'speed': 0.3, 'size': 0.4},
        'fog': {'type': 'fog', 'density': 0.02, 'color': 'theme'},
        'mist': {'type': 'fog', 'density': 0.01, 'color': 'theme'},
        'glow': {'type': 'bloom', 'strength': 1.5, 'radius': 0.4},
        'particles': {'type': 'particles', 'count': 2000, 'color': 'theme', 'motion': 'float', 'speed': 0.1, 'size': 0.1},
        'spores': {'type': 'particles', 'count': 1200, 'color': 'lime', 'motion': 'drift', 'speed': 0.15, 'size': 0.2},
        'ash': {'type': 'particles', 'count': 2000, 'color': 'gray', 'motion': 'downward_slow', 'speed': 0.1, 'size': 0.15},
        'fireflies': {'type': 'particles', 'count': 500, 'color': 'gold', 'motion': 'wander', 'speed': 0.3, 'size': 0.25},
        'bubbles': {'type': 'particles', 'count': 800, 'color': 'cyan', 'motion': 'upward', 'speed': 0.4, 'size': 0.3},
    }
    
    ANIMATIONS = {
        'floating': {'type': 'position', 'axis': 'y', 'amplitude': 2, 'duration': 4, 'ease': 'sine.inOut'},
        'rotating': {'type': 'rotation', 'axis': 'y', 'speed': 0.5, 'duration': 20, 'ease': 'none'},
        'pulsing': {'type': 'scale', 'axis': 'all', 'amplitude': 0.2, 'duration': 2, 'ease': 'sine.inOut'},
        'orbiting': {'type': 'orbit', 'radius': 10, 'speed': 0.001, 'axis': 'y'},
        'weaving': {'type': 'curve', 'speed': 0.0005, 'loop': True},
        'breathing': {'type': 'scale', 'axis': 'all', 'amplitude': 0.1, 'duration': 3, 'ease': 'sine.inOut'},
        'shimmering': {'type': 'emissive', 'amplitude': 0.3, 'duration': 1.5, 'ease': 'sine.inOut'},
        'undulating': {'type': 'position_wave', 'axis': 'y', 'amplitude': 1, 'frequency': 0.5, 'phase_offset': True},
    }
    
    LAYOUTS = {
        'grid': {'type': 'grid', 'spacing': 6, 'count': 12, 'pattern': 'square', 'randomness': 0.2},
        'circle': {'type': 'radial', 'radius': 20, 'count': 12, 'pattern': 'circle', 'randomness': 0.1},
        'cluster': {'type': 'random', 'range': 30, 'count': 20, 'pattern': 'sphere', 'randomness': 0.8},
        'spiral': {'type': 'spiral', 'radius': 15, 'count': 20, 'height': 20, 'turns': 3, 'randomness': 0.1},
        'linear': {'type': 'line', 'length': 50, 'count': 15, 'pattern': 'straight', 'randomness': 0.1},
        'network': {'type': 'graph', 'nodes': 25, 'connections': 40, 'pattern': 'neural', 'randomness': 0.3},
        'fractal': {'type': 'recursive', 'depth': 4, 'branching': 3, 'pattern': 'tree', 'randomness': 0.2},
        'concentric': {'type': 'rings', 'rings': 5, 'density': 'increasing', 'pattern': 'target', 'randomness': 0.1},
    }
    
    LIGHTING = {
        'neon': {'ambient': 0.4, 'points': 3, 'colors': 'theme', 'intensity': 2.0},
        'soft': {'ambient': 0.8, 'directional': 1, 'colors': 'warm', 'intensity': 0.6},
        'harsh': {'ambient': 0.2, 'directional': 2, 'colors': 'cool', 'intensity': 1.5, 'shadows': True},
        'dramatic': {'ambient': 0.1, 'spot': 2, 'colors': 'contrast', 'intensity': 3.0, 'shadows': True},
        'ethereal': {'ambient': 0.6, 'hemisphere': True, 'colors': 'sky', 'intensity': 1.0},
        'bioluminescent': {'ambient': 0.3, 'points': 8, 'colors': 'neon', 'intensity': 1.5, 'attenuation': True},
    }


class KimiAPIClient:
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key =  os.getenv("KIMI_API_KEY")
        if not self.api_key:
            raise ValueError("KIMI_API_KEY not provided")
        self.base_url = "https://api.moonshot.ai/v1"
        self.model = "kimi-k2-turbo-preview"  # or specific version
        
    async def extract_concepts(self, topic: str, description: str) -> ExtractedConcepts:
        system_prompt = """You are an expert Visual Concept Extractor for 3D graphics generation.
Your task is to analyze user descriptions and extract structured visual concepts for Three.js scene generation.

Extract the following with high precision:
1. MATERIALS: Physical surface properties (obsidian, crystal, neon, bioluminescent, etc.)
2. SHAPES: Geometric forms (tower, sphere, ribbon, monolith, shard, helix, etc.)
3. COLORS: Specific color names (violet, emerald, cyan, crimson, etc.)
4. ATMOSPHERE: Environmental effects (rain, fog, embers, spores, bubbles, etc.)
5. ANIMATIONS: Motion types (floating, pulsing, orbiting, weaving, breathing, etc.)
6. LAYOUT: Spatial arrangement (grid, spiral, cluster, network, concentric, etc.)
7. LIGHTING: Illumination style (neon, soft, harsh, dramatic, bioluminescent, etc.)
8. MOOD: Emotional tone (mysterious, serene, chaotic, majestic, intimate)
9. SCALE: Size perception (intimate, grand, vast, infinite)
10. TEMPORAL: Time quality (static, dynamic, evolving, decaying)

Rules:
- Be specific and technical
- Infer from metaphorical language
- Identify primary vs secondary elements
- Consider cultural/visual references
- Map abstract concepts to concrete visual parameters

Output strictly as JSON with no markdown formatting."""
        
        user_prompt = f"""TOPIC: {topic}
DESCRIPTION: {description}

Analyze this scene description and extract all visual concepts. Return as JSON:
{{
    "materials": ["material1", "material2"],
    "shapes": ["shape1", "shape2"],
    "colors": ["color1", "color2"],
    "atmosphere": ["effect1"],
    "animations": ["animation1", "animation2"],
    "layout": "layout_type",
    "lighting": "lighting_type",
    "mood": "mood_description",
    "scale": "scale_type",
    "temporal": "temporal_quality"
}}"""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,  # Lower for consistent extraction
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"}
                }
                
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Kimi API error: {error_text}")
                        raise Exception(f"API error: {response.status}")
                    
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    
                    return ExtractedConcepts(
                        topic=topic,
                        materials=parsed.get("materials", ["obsidian"]),
                        shapes=parsed.get("shapes", ["tower"]),
                        colors=parsed.get("colors", ["violet"]),
                        atmosphere=parsed.get("atmosphere", ["fog"]),
                        animations=parsed.get("animations", ["floating"]),
                        layout=parsed.get("layout", "grid"),
                        lighting=parsed.get("lighting", "neon"),
                        mood=parsed.get("mood", "mysterious"),
                        scale=parsed.get("scale", "grand"),
                        temporal=parsed.get("temporal", "dynamic")
                    )
                    
        except Exception as e:
            logger.error(f"Concept extraction failed: {e}")
            # Fallback to rule-based extraction
            return self._fallback_extraction(topic, description)
    
    def _fallback_extraction(self, topic: str, description: str) -> ExtractedConcepts:
        lower_desc = description.lower()
        lower_topic = topic.lower()
        
        # Simple keyword matching
        materials = []
        for mat in ConceptDatabase.MATERIALS.keys():
            if mat in lower_desc:
                materials.append(mat)
        
        shapes = []
        for shape in ConceptDatabase.SHAPES.keys():
            if shape in lower_desc:
                shapes.append(shape)
        
        colors = []
        for color in ConceptDatabase.COLORS.keys():
            if color in lower_desc:
                colors.append(color)
        
        # Defaults
        if not materials:
            materials = ["obsidian"]
        if not shapes:
            shapes = ["tower"]
        if not colors:
            colors = ["violet", "emerald"]
        
        return ExtractedConcepts(
            topic=topic,
            materials=materials,
            shapes=shapes,
            colors=colors[:2],
            atmosphere=["fog"] if "fog" in lower_desc or "mist" in lower_desc else [],
            animations=["floating"] if "float" in lower_desc else ["rotating"],
            layout="grid",
            lighting="neon",
            mood="mysterious",
            scale="grand",
            temporal="dynamic"
        )
    
    async def enhance_description(self, concepts: ExtractedConcepts) -> str:       
        system_prompt = """You are an expert Visual Describer for 3D scene generation.
Expand structured concepts into rich, technical visual descriptions that guide code generation.

Focus on:
- Spatial relationships and composition
- Material interactions with light
- Atmospheric depth and layering
- Animation timing and rhythm
- Color harmony and contrast
- Scale and perspective cues

Write in present tense, visual-first, technical but evocative."""
        
        user_prompt = f"""Generate a detailed visual description for a 3D scene with these parameters:
- Topic: {concepts.topic}
- Mood: {concepts.mood}
- Scale: {concepts.scale}
- Temporal quality: {concepts.temporal}
- Materials: {', '.join(concepts.materials)}
- Shapes: {', '.join(concepts.shapes)}
- Colors: {', '.join(concepts.colors)}
- Atmosphere: {', '.join(concepts.atmosphere)}
- Animations: {', '.join(concepts.animations)}
- Layout: {concepts.layout}
- Lighting: {concepts.lighting}

Describe the scene as if viewing it in real-time. Include:
1. Overall composition and spatial arrangement
2. How materials respond to lighting
3. Atmospheric effects and their movement
4. Animation timing and inter-object relationships
5. Camera perspective and viewer experience

Keep under 300 words but be technically specific."""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 600
                }
                
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                    
        except Exception as e:
            logger.error(f"Description enhancement failed: {e}")
            return self._fallback_description(concepts)
    
    def _fallback_description(self, concepts: ExtractedConcepts) -> str:
        return f"""A {concepts.scale} {concepts.mood} scene featuring {concepts.shapes[0]} forms 
        crafted from {concepts.materials[0]}. The composition follows a {concepts.layout} arrangement 
        illuminated by {concepts.lighting} lighting in {concepts.colors[0]} and {concepts.colors[1]} hues. 
        {concepts.animations[0]} motion brings {concepts.temporal} energy to the atmosphere 
        where {concepts.atmosphere[0] if concepts.atmosphere else 'mist'} drifts through the space."""
    
    async def generate_code(self, concepts: ExtractedConcepts, enhanced_desc: str, 
                           technical_spec: TechnicalSpec) -> str:       
        system_prompt = """You are an expert Three.js Developer and Creative Technologist.
Generate production-ready, optimized 3D scene code based on visual specifications.

Requirements:
- Single HTML file with embedded CSS/JS
- Three.js r128+ via CDN
- GSAP 3.x for animations
- OrbitControls with damping
- Responsive design
- Performance optimized (max 2000 draw calls, instancing where possible)
- Clean, commented code
- No external assets (procedural generation only)

Technical standards:
- Use BufferGeometry for particles
- Implement proper dispose patterns
- Tone mapping for HDR-like lighting
- Fog for depth cues
- Efficient animation loops
- Mobile-friendly defaults

Output ONLY the complete HTML code, no markdown, no explanations."""
        
        # Build technical context
        materials_code = json.dumps({k: ConceptDatabase.MATERIALS[k] for k in concepts.materials if k in ConceptDatabase.MATERIALS}, indent=2)
        shapes_code = json.dumps({k: ConceptDatabase.SHAPES[k] for k in concepts.shapes if k in ConceptDatabase.SHAPES}, indent=2)
        colors_code = json.dumps({k: ConceptDatabase.COLORS[k] for k in concepts.colors if k in ConceptDatabase.COLORS}, indent=2)
        
        user_prompt = f"""Generate a complete Three.js scene HTML file.

VISUAL SPECIFICATION:
{enhanced_desc}

STRUCTURED PARAMETERS:
- Layout: {concepts.layout}
- Lighting: {concepts.lighting}
- Animations: {', '.join(concepts.animations)}
- Atmosphere: {', '.join(concepts.atmosphere)}

TECHNICAL REFERENCE:
Materials: {materials_code}
Shapes: {shapes_code}
Colors: {colors_code}

TECHNICAL SPEC:
- Fog density: {technical_spec.fog_density}
- Camera: {technical_spec.camera_position}
- Particles: {technical_spec.particle_count}
- Post-processing: {technical_spec.post_processing}

TITLE: {concepts.topic}

Generate the complete HTML starting with <!DOCTYPE html> and ending with </html>.
Include all necessary CDNs and create a visually stunning, interactive scene."""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.model,  # or "kimi-k1" for code generation
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,  # Lower for code
                    "max_tokens": 4000
                }
                
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    data = await response.json()
                    code = data["choices"][0]["message"]["content"]
                    
                    # Clean up code (remove markdown if present)
                    code = re.sub(r'^```html\s*', '', code)
                    code = re.sub(r'```\s*$', '', code)
                    code = code.strip()
                    
                    return code
                    
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return self._fallback_code_generation(concepts, technical_spec)
    
    def _fallback_code_generation(self, concepts: ExtractedConcepts, spec: TechnicalSpec) -> str:
        # This would return a simplified version of the Aetheria template
        # adapted to the concepts - implementation omitted for brevity
        return "<!-- Fallback code generation - API unavailable -->"


class SceneCompositionEngine:   
    def __init__(self):
        self.db = ConceptDatabase()
    
    def plan_space(self, concepts: ExtractedConcepts) -> Dict:
        """Determine spatial composition strategy"""
        layout_config = self.db.LAYOUTS.get(concepts.layout, self.db.LAYOUTS['grid'])
        
        # Adjust based on scale
        if concepts.scale == 'intimate':
            layout_config['range'] = layout_config.get('range', 30) * 0.5
            layout_config['spacing'] = layout_config.get('spacing', 6) * 0.7
        elif concepts.scale == 'vast':
            layout_config['range'] = layout_config.get('range', 30) * 2
            layout_config['count'] = int(layout_config.get('count', 12) * 1.5)
        
        # Adjust based on mood
        if concepts.mood == 'chaotic':
            layout_config['randomness'] = min(layout_config.get('randomness', 0.2) * 2, 0.9)
        
        return layout_config
    
    def design_objects(self, concepts: ExtractedConcepts) -> List[Dict]:
        objects = []
        
        for i, shape_name in enumerate(concepts.shapes[:3]):  # Max 3 shape types
            shape_data = self.db.SHAPES.get(shape_name, self.db.SHAPES['tower'])
            material_name = concepts.materials[i % len(concepts.materials)]
            material_data = self.db.MATERIALS.get(material_name, self.db.MATERIALS['obsidian'])
            
            obj = {
                'id': f"{shape_name}_{i}",
                'shape': shape_data,
                'material': material_data,
                'primary': i == 0,
                'animation': concepts.animations[i % len(concepts.animations)] if concepts.animations else None
            }
            objects.append(obj)
        
        return objects
    
    def design_atmosphere(self, concepts: ExtractedConcepts) -> Dict:
        effects = {}
        
        for atmo_name in concepts.atmosphere:
            if atmo_name in self.db.ATMOSPHERE:
                atmo_data = self.db.ATMOSPHERE[atmo_name].copy()
                # Map theme color
                if atmo_data.get('color') == 'theme':
                    atmo_data['color'] = concepts.colors[0] if concepts.colors else 'cyan'
                effects[atmo_name] = atmo_data
        
        # Add lighting configuration
        effects['lighting'] = self.db.LIGHTING.get(concepts.lighting, self.db.LIGHTING['neon'])
        
        return effects
    
    def calculate_technical_spec(self, concepts: ExtractedConcepts) -> TechnicalSpec:
        # Base spec
        spec = TechnicalSpec(
            fog_density=0.015,
            camera_position=(30, 20, 40),
            particle_count=1000,
            shadow_map_size=2048,
            antialias=True,
            tone_mapping="ReinhardToneMapping",
            post_processing=[]
        )
        
        # Adjust based on atmosphere
        if 'fog' in concepts.atmosphere or 'mist' in concepts.atmosphere:
            spec.fog_density = 0.025
        
        # Adjust based on scale
        if concepts.scale == 'intimate':
            spec.camera_position = (15, 10, 20)
        elif concepts.scale == 'vast':
            spec.camera_position = (60, 40, 80)
            spec.particle_count = 2000
        
        # Post-processing
        if concepts.lighting in ['neon', 'dramatic', 'bioluminescent']:
            spec.post_processing.append('bloom')
        
        if any(a in concepts.animations for a in ['pulsing', 'shimmering']):
            spec.post_processing.append('emissive_bloom')
        
        return spec


class VisualGenesisAgent:   
    def __init__(self, api_key: Optional[str] = None):
        self.kimi = KimiAPIClient(api_key)
        self.composer = SceneCompositionEngine()
        self.generation_history = []
    
    async def generate(self, topic: str, description: str, 
                      style_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Main generation pipeline
        """
        logger.info(f"Starting generation for: {topic}")
        start_time = datetime.now()
        
        # Stage 1: Concept Extraction (Kimi API)
        logger.info("Stage 1: Extracting concepts...")
        concepts = await self.kimi.extract_concepts(topic, description)
        
        # Apply style hint if provided
        if style_hint:
            concepts = self._apply_style_hint(concepts, style_hint)
        
        # Stage 2: Composition Planning
        logger.info("Stage 2: Planning composition...")
        space_plan = self.composer.plan_space(concepts)
        objects = self.composer.design_objects(concepts)
        atmosphere = self.composer.design_atmosphere(concepts)
        tech_spec = self.composer.calculate_technical_spec(concepts)
        
        # Stage 3: Visual Enhancement (Kimi API)
        logger.info("Stage 3: Enhancing description...")
        enhanced_desc = await self.kimi.enhance_description(concepts)
        
        # Stage 4: Code Synthesis (Kimi API)
        logger.info("Stage 4: Generating code...")
        html_code = await self.kimi.generate_code(concepts, enhanced_desc, tech_spec)
        
        # Compile result
        generation_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            'metadata': {
                'topic': topic,
                'generation_time_seconds': generation_time,
                'timestamp': datetime.now().isoformat(),
                'model': self.kimi.model
            },
            'concepts': concepts.to_dict(),
            'technical_spec': {
                'fog_density': tech_spec.fog_density,
                'camera_position': tech_spec.camera_position,
                'particle_count': tech_spec.particle_count,
                'post_processing': tech_spec.post_processing
            },
            'composition': {
                'space_plan': space_plan,
                'objects': objects,
                'atmosphere': atmosphere
            },
            'enhanced_description': enhanced_desc,
            'generated_code': html_code,
            'file_name': f"{topic.lower().replace(' ', '_')}_scene.html"
        }
        
        self.generation_history.append(result)
        logger.info(f"Generation complete in {generation_time:.2f}s")
        
        return result
    
    def _apply_style_hint(self, concepts: ExtractedConcepts, hint: str) -> ExtractedConcepts:
        hint = hint.lower()
        
        style_presets = {
            'cyberpunk': {
                'materials': ['obsidian', 'neon', 'steel'],
                'colors': ['violet', 'emerald', 'cyan'],
                'atmosphere': ['rain', 'fog', 'glow'],
                'lighting': 'neon',
                'animations': ['pulsing', 'floating']
            },
            'ethereal': {
                'materials': ['crystal', 'glass', 'ice'],
                'colors': ['azure', 'white', 'lavender'],
                'atmosphere': ['mist', 'particles', 'glow'],
                'lighting': 'ethereal',
                'animations': ['floating', 'breathing']
            },
            'industrial': {
                'materials': ['steel', 'rusted', 'obsidian'],
                'colors': ['orange', 'steel', 'black'],
                'atmosphere': ['embers', 'fog', 'ash'],
                'lighting': 'harsh',
                'animations': ['rotating', 'shimmering']
            },
            'organic': {
                'materials': ['organic', 'bioluminescent', 'crystal'],
                'colors': ['emerald', 'lime', 'gold'],
                'atmosphere': ['spores', 'mist', 'fireflies'],
                'lighting': 'bioluminescent',
                'animations': ['breathing', 'undulating']
            }
        }
        
        if hint in style_presets:
            preset = style_presets[hint]
            for key, value in preset.items():
                setattr(concepts, key, value)
        
        return concepts
    
    def save_code(self, result: Dict, output_dir: str = "/3Dsite") -> str:
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, result['file_name'])
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result['generated_code'])
        
        logger.info(f"Saved to: {file_path}")
        return file_path


# Example usage and CLI interface
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Visual Genesis Agent')
    parser.add_argument('--topic', '-t', required=True, help='Scene topic/title')
    parser.add_argument('--description', '-d', required=True, help='Visual description')
    parser.add_argument('--style', '-s', choices=['cyberpunk', 'ethereal', 'industrial', 'organic'], 
                       help='Style preset')
    parser.add_argument('--output', '-o', default='./3Dsite', help='Output directory')
    parser.add_argument('--api-key', '-k', help='sk-2sMY8kEJTVTT9UvKtOMaSvjTtQMUMjNZsRQwGUnZjvVfDVVX')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = VisualGenesisAgent(api_key=args.api_key)
    
    # Generate
    result = await agent.generate(
        topic=args.topic,
        description=args.description,
        style_hint=args.style
    )
    
    # Save
    file_path = agent.save_code(result, args.output)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"GENERATION COMPLETE: {result['metadata']['topic']}")
    print(f"{'='*60}")
    print(f"File: {file_path}")
    print(f"Time: {result['metadata']['generation_time_seconds']:.2f}s")
    print(f"Colors: {', '.join(result['concepts']['colors'])}")
    print(f"Materials: {', '.join(result['concepts']['materials'])}")
    print(f"Shapes: {', '.join(result['concepts']['shapes'])}")
    print(f"Layout: {result['concepts']['layout']}")
    print(f"{'='*60}\n")
    
    # Also print enhanced description
    print("VISUAL DESCRIPTION:")
    print(result['enhanced_description'][:300] + "...\n")


# if __name__ == "__main__":
#     asyncio.run(main())