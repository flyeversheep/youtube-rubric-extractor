#!/usr/bin/env python3
"""
Extract coaching rubric from YouTube tutorial

Usage:
    python extract_rubric.py --url "https://youtube.com/watch?v=..." --title "Fast Castle Guide"
    python extract_rubric.py --url "https://youtube.com/watch?v=..." --output my_rubric.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / 'utils'))

from youtube import download_transcript, chunk_transcript, get_video_metadata
from llm_client import get_client
from rubric_parser import parse_rubric_json, generate_rubric_id, merge_rubrics


def load_prompt() -> str:
    """Load the extraction prompt from file"""
    prompt_path = Path(__file__).parent / 'prompts' / 'extract_rubric.txt'
    if prompt_path.exists():
        return prompt_path.read_text()
    
    # Fallback prompt
    return """Extract a structured coaching rubric from this AoE IV tutorial transcript.
Return as JSON with: title, difficulty, archetype, phases (with key_actions, success_criteria, common_mistakes), benchmarks (timings), and decision_points."""


def extract_from_chunk(chunk: str, prompt: str, client) -> dict:
    """Extract rubric from a single transcript chunk"""
    full_prompt = f"{prompt}\n\n## Transcript\n\n{chunk}\n\n## Extracted Rubric (JSON):"
    
    result = client.complete_with_retry(
        prompt=full_prompt,
        system_prompt="You are an expert AoE IV coach extracting structured rubrics from tutorials.",
        temperature=0.3,
        json_mode=True
    )
    
    if not result['success']:
        print(f"Error: {result['error']}")
        return None
    
    try:
        return parse_rubric_json(result['content'])
    except ValueError as e:
        print(f"Parse error: {e}")
        return None


def extract_rubric(url: str, custom_title: str = None) -> dict:
    """Main extraction pipeline"""
    print(f"📥 Downloading transcript from: {url}")
    
    # Get metadata first
    metadata = get_video_metadata(url)
    print(f"📹 Title: {metadata['title']}")
    print(f"👤 Author: {metadata['author']}")
    print(f"⏱️  Duration: {metadata['duration'] // 60}m {metadata['duration'] % 60}s")
    
    # Download transcript
    transcript = download_transcript(url)
    if not transcript:
        print("❌ No transcript available for this video")
        return None
    
    print(f"📝 Transcript length: {len(transcript)} characters")
    
    # Initialize LLM
    client = get_client()
    if not client.is_available():
        print("❌ LLM not configured. Set OPENAI_API_KEY or ZAI_API_KEY")
        return None
    
    # Load prompt
    prompt = load_prompt()
    
    # Chunk if necessary
    chunks = chunk_transcript(transcript, chunk_size=4000, overlap=500)
    print(f"🔄 Processing {len(chunks)} chunk(s)...")
    
    # Extract from each chunk
    rubrics = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  Processing chunk {i}/{len(chunks)}...")
        rubric = extract_from_chunk(chunk, prompt, client)
        if rubric:
            rubrics.append(rubric)
    
    if not rubrics:
        print("❌ Failed to extract rubric from any chunk")
        return None
    
    # Merge if multiple chunks
    if len(rubrics) > 1:
        print("🔄 Merging chunks...")
        final_rubric = merge_rubrics(rubrics)
    else:
        final_rubric = rubrics[0]
    
    # Add metadata
    final_rubric['source_url'] = url
    final_rubric['video_title'] = metadata['title']
    final_rubric['video_author'] = metadata['author']
    final_rubric['video_duration'] = metadata['duration']
    
    # Use custom title if provided
    if custom_title:
        final_rubric['title'] = custom_title
    
    return final_rubric


def save_rubric(rubric: dict, output_path: str = None):
    """Save rubric to file"""
    # Generate ID and filename
    rubric_id = generate_rubric_id(
        rubric.get('title', 'untitled'),
        rubric.get('video_author', 'unknown')
    )
    rubric['id'] = rubric_id
    
    # Determine output path
    if output_path:
        filepath = Path(output_path)
    else:
        library_dir = Path(__file__).parent / 'rubric_library'
        library_dir.mkdir(exist_ok=True)
        filepath = library_dir / f"{rubric_id}.json"
    
    # Save
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(rubric, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved rubric to: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description='Extract coaching rubric from YouTube tutorial'
    )
    parser.add_argument('--url', required=True, help='YouTube video URL')
    parser.add_argument('--title', help='Custom title for the rubric')
    parser.add_argument('--output', '-o', help='Output file path (default: rubric_library/<id>.json)')
    parser.add_argument('--print', '-p', action='store_true', help='Print rubric to stdout')
    
    args = parser.parse_args()
    
    # Extract
    rubric = extract_rubric(args.url, args.title)
    if not rubric:
        sys.exit(1)
    
    # Save
    filepath = save_rubric(rubric, args.output)
    
    # Print if requested
    if args.print:
        print("\n" + "="*60)
        print(json.dumps(rubric, indent=2))
    
    print(f"\n🎉 Done! Rubric ID: {rubric['id']}")


if __name__ == '__main__':
    main()
