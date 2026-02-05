#!/usr/bin/env python3
"""
List all extracted rubrics in the library

Usage:
    python list_rubrics.py
    python list_rubrics.py --filter fast_castle
    python list_rubrics.py --format table
"""
import argparse
import json
from pathlib import Path
from typing import List, Dict


def load_rubrics(library_dir: Path) -> List[Dict]:
    """Load all rubrics from library"""
    rubrics = []
    
    if not library_dir.exists():
        return rubrics
    
    for json_file in library_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                rubric = json.load(f)
                rubric['_filepath'] = json_file.name
                rubrics.append(rubric)
        except Exception as e:
            print(f"Warning: Failed to load {json_file}: {e}")
    
    return rubrics


def format_time(seconds: int) -> str:
    """Format seconds as MM:SS"""
    if seconds is None:
        return 'N/A'
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def print_table(rubrics: List[Dict]):
    """Print rubrics as formatted table"""
    if not rubrics:
        print("No rubrics found. Extract some with extract_rubric.py!")
        return
    
    # Header
    print(f"{'ID':<30} {'Difficulty':<12} {'Archetype':<20} {'FC Time':<10} {'Phases':<8}")
    print("-" * 90)
    
    # Rows
    for r in rubrics:
        rubric_id = r.get('id', 'unknown')[:28]
        difficulty = r.get('difficulty', 'unknown')[:10]
        archetype = r.get('archetype', 'unknown')[:18]
        
        fc_time = r.get('benchmarks', {}).get('castle_age')
        fc_str = format_time(fc_time) if fc_time else 'N/A'
        
        phases = len(r.get('phases', []))
        
        print(f"{rubric_id:<30} {difficulty:<12} {archetype:<20} {fc_str:<10} {phases:<8}")
    
    print(f"\nTotal: {len(rubrics)} rubric(s)")


def print_detailed(rubrics: List[Dict]):
    """Print detailed rubric info"""
    if not rubrics:
        print("No rubrics found. Extract some with extract_rubric.py!")
        return
    
    for i, r in enumerate(rubrics, 1):
        print(f"\n{'='*60}")
        print(f"#{i}: {r.get('title', 'Untitled')}")
        print(f"   ID: {r.get('id', 'unknown')}")
        print(f"   File: {r.get('_filepath', 'unknown')}")
        
        print(f"\n   Difficulty: {r.get('difficulty', 'unknown')}")
        print(f"   Archetype: {r.get('archetype', 'unknown')}")
        
        civs = r.get('civilizations', [])
        if civs:
            print(f"   Civilizations: {', '.join(civs)}")
        
        maps = r.get('map_types', [])
        if maps:
            print(f"   Map Types: {', '.join(maps)}")
        
        benchmarks = r.get('benchmarks', {})
        if benchmarks.get('castle_age'):
            print(f"\n   Benchmarks:")
            if benchmarks.get('feudal_age'):
                print(f"     Feudal: {format_time(benchmarks['feudal_age'])}")
            if benchmarks.get('castle_age'):
                print(f"     Castle: {format_time(benchmarks['castle_age'])}")
        
        phases = r.get('phases', [])
        if phases:
            print(f"\n   Phases ({len(phases)}):")
            for p in phases:
                actions = len(p.get('key_actions', []))
                mistakes = len(p.get('common_mistakes', []))
                print(f"     • {p.get('name', 'Phase')} ({actions} actions, {mistakes} mistakes)")
        
        source = r.get('source_url', '')
        if source:
            print(f"\n   Source: {source}")


def main():
    parser = argparse.ArgumentParser(description='List extracted rubrics')
    parser.add_argument('--filter', '-f', help='Filter by archetype or keyword')
    parser.add_argument('--format', choices=['table', 'detailed'], default='table',
                       help='Output format')
    
    args = parser.parse_args()
    
    # Load rubrics
    library_dir = Path(__file__).parent / 'rubric_library'
    rubrics = load_rubrics(library_dir)
    
    # Filter if requested
    if args.filter:
        filter_lower = args.filter.lower()
        rubrics = [
            r for r in rubrics
            if filter_lower in r.get('archetype', '').lower()
            or filter_lower in r.get('title', '').lower()
            or filter_lower in r.get('id', '').lower()
        ]
    
    # Print
    if args.format == 'table':
        print_table(rubrics)
    else:
        print_detailed(rubrics)


if __name__ == '__main__':
    main()
