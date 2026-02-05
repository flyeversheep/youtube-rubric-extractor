"""
Parse LLM output into structured rubric format with validation
"""
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime


def parse_rubric_json(content: str) -> Dict[str, Any]:
    """
    Parse LLM response into structured rubric
    
    Args:
        content: Raw LLM response (should be JSON)
    
    Returns:
        Parsed and validated rubric dict
    """
    # Try to extract JSON if wrapped in markdown
    if '```json' in content:
        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if match:
            content = match.group(1)
    elif '```' in content:
        match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
        if match:
            content = match.group(1)
    
    # Clean up common issues
    content = content.strip()
    
    try:
        rubric = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM response: {e}\nContent preview: {content[:500]}")
    
    # Validate and normalize
    rubric = _validate_rubric(rubric)
    
    return rubric


def _validate_rubric(rubric: Dict) -> Dict:
    """Validate and fill in defaults for rubric structure"""
    required_fields = ['title', 'difficulty', 'archetype']
    
    for field in required_fields:
        if field not in rubric or not rubric[field]:
            rubric[field] = 'unknown'
    
    # Ensure arrays exist
    rubric.setdefault('civilizations', [])
    rubric.setdefault('map_types', ['any'])
    rubric.setdefault('phases', [])
    rubric.setdefault('decision_points', [])
    rubric.setdefault('counters', {})
    rubric.setdefault('key_insights', [])
    
    # Validate phases
    for phase in rubric.get('phases', []):
        phase.setdefault('key_actions', [])
        phase.setdefault('success_criteria', [])
        phase.setdefault('common_mistakes', [])
        
        # Validate actions
        for action in phase.get('key_actions', []):
            action.setdefault('importance', 'important')
    
    # Validate benchmarks
    rubric.setdefault('benchmarks', {})
    for key in ['feudal_age', 'castle_age', 'imperial_age', 'second_tc', 'third_tc', 
                'villagers_at_10min', 'villagers_at_castle']:
        rubric['benchmarks'].setdefault(key, None)
    
    # Add metadata
    rubric['_meta'] = {
        'extracted_at': datetime.now().isoformat(),
        'version': '1.0'
    }
    
    return rubric


def generate_rubric_id(title: str, author: str = 'unknown') -> str:
    """Generate a unique ID for the rubric"""
    # Clean title for ID
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())
    clean = re.sub(r'\s+', '_', clean.strip())
    clean = clean[:50]  # Limit length
    
    # Add archetype hint if available
    return clean


def merge_rubrics(rubrics: list) -> Dict:
    """
    Merge multiple rubric chunks into one coherent rubric
    
    This is used when processing a long video in chunks
    """
    if not rubrics:
        return {}
    
    if len(rubrics) == 1:
        return rubrics[0]
    
    # Start with first rubric
    merged = rubrics[0].copy()
    
    # Merge phases (avoid duplicates)
    existing_phases = {p['name'] for p in merged.get('phases', [])}
    for rubric in rubrics[1:]:
        for phase in rubric.get('phases', []):
            if phase['name'] not in existing_phases:
                merged['phases'].append(phase)
                existing_phases.add(phase['name'])
    
    # Merge key insights
    existing_insights = set(merged.get('key_insights', []))
    for rubric in rubrics[1:]:
        for insight in rubric.get('key_insights', []):
            if insight not in existing_insights:
                merged['key_insights'].append(insight)
                existing_insights.add(insight)
    
    # Update benchmarks if more specific
    for rubric in rubrics[1:]:
        for key, value in rubric.get('benchmarks', {}).items():
            if value is not None and merged.get('benchmarks', {}).get(key) is None:
                merged['benchmarks'][key] = value
    
    # Merge decision points
    existing_triggers = {dp['trigger'] for dp in merged.get('decision_points', [])}
    for rubric in rubrics[1:]:
        for dp in rubric.get('decision_points', []):
            if dp['trigger'] not in existing_triggers:
                merged['decision_points'].append(dp)
                existing_triggers.add(dp['trigger'])
    
    return merged


def format_rubric_for_display(rubric: Dict) -> str:
    """Format rubric as human-readable text"""
    lines = []
    
    lines.append(f"# {rubric.get('title', 'Untitled Rubric')}")
    lines.append(f"**Difficulty:** {rubric.get('difficulty', 'unknown')}")
    lines.append(f"**Archetype:** {rubric.get('archetype', 'unknown')}")
    lines.append("")
    
    if rubric.get('overview'):
        lines.append(f"## Overview")
        lines.append(rubric['overview'])
        lines.append("")
    
    if rubric.get('benchmarks'):
        lines.append("## Benchmarks")
        for key, value in rubric['benchmarks'].items():
            if value is not None:
                if 'age' in key or 'tc' in key:
                    mins = value // 60
                    secs = value % 60
                    lines.append(f"- {key}: {mins}:{secs:02d}")
                else:
                    lines.append(f"- {key}: {value}")
        lines.append("")
    
    if rubric.get('phases'):
        lines.append("## Phases")
        for phase in rubric['phases']:
            lines.append(f"\n### {phase.get('name', 'Phase')}")
            if phase.get('description'):
                lines.append(phase['description'])
            
            if phase.get('key_actions'):
                lines.append("\n**Key Actions:**")
                for action in phase['key_actions']:
                    lines.append(f"- {action.get('action', '')} ({action.get('timing', '')})")
            
            if phase.get('success_criteria'):
                lines.append("\n**Success Criteria:**")
                for criteria in phase['success_criteria']:
                    lines.append(f"- ✅ {criteria}")
            
            if phase.get('common_mistakes'):
                lines.append("\n**Common Mistakes:**")
                for mistake in phase['common_mistakes']:
                    lines.append(f"- ❌ {mistake.get('mistake', '')}")
                    if mistake.get('fix'):
                        lines.append(f"  → Fix: {mistake['fix']}")
    
    return '\n'.join(lines)
