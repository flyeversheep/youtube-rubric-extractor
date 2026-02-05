#!/usr/bin/env python3
"""
Evaluate a real game against extracted rubrics

Usage:
    python evaluate_game.py --rubric fast_castle --game-data game.json
    python evaluate_game.py --rubric fast_castle --profile 17689761 --game 182257348
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent / 'utils'))

from llm_client import get_client


def load_rubric(rubric_id: str) -> Dict:
    """Load rubric by ID"""
    # Try direct path first
    filepath = Path(__file__).parent / 'rubric_library' / f"{rubric_id}.json"
    
    if not filepath.exists():
        # Try partial match
        library_dir = Path(__file__).parent / 'rubric_library'
        for json_file in library_dir.glob('*.json'):
            if rubric_id.lower() in json_file.stem.lower():
                filepath = json_file
                break
    
    if not filepath.exists():
        raise FileNotFoundError(f"Rubric not found: {rubric_id}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_game_data(filepath: str) -> Dict:
    """Load game data from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def fetch_game_from_api(profile_id: str, game_id: str) -> Dict:
    """Fetch game data from AoE4 World API (placeholder)"""
    # This would integrate with your aoe4-coach backend
    print(f"Note: API integration not yet implemented")
    print(f"Please export game data to JSON first:")
    print(f"  curl http://localhost:8000/api/game/{profile_id}/{game_id} > game.json")
    raise NotImplementedError("API fetch not implemented")


def format_game_summary(game_data: Dict) -> str:
    """Format game data as readable summary for LLM"""
    player = game_data.get('player', {})
    opponent = game_data.get('opponent', {})
    timings = game_data.get('timings', {})
    
    lines = [
        f"Game: {game_data.get('game', {}).get('map', 'Unknown')}",
        f"Player: {player.get('name')} ({player.get('civilization')}) - {player.get('result', 'unknown').upper()}",
        f"Opponent: {opponent.get('name')} ({opponent.get('civilization')})",
        f"APM: {player.get('apm', 'N/A')}",
        "",
        "Age Up Timings:",
        f"  Feudal: {timings.get('feudal_age', {}).get('seconds', 'N/A')}s",
        f"  Castle: {timings.get('castle_age', {}).get('seconds', 'N/A')}s",
        f"  Imperial: {timings.get('imperial_age', {}).get('seconds', 'N/A')}s",
        "",
        f"Resources Gathered: {player.get('resources_gathered', {})}",
        f"Final Score: {player.get('final_score', {})}",
    ]
    
    # Add build order summary
    build_order = game_data.get('build_order', [])
    if build_order:
        lines.append("")
        lines.append("Key Build Order Items (first 10):")
        # Sort by first finished time
        sorted_bo = sorted(build_order, key=lambda x: x.get('finished', [9999])[0])[:10]
        for item in sorted_bo:
            time = item.get('finished', [0])[0]
            item_id = item.get('id', 'unknown')
            item_type = item.get('type', 'unknown')
            mins = time // 60
            secs = time % 60
            lines.append(f"  [{mins}:{secs:02d}] {item_type}: {item_id}")
    
    return '\n'.join(lines)


def evaluate_against_rubric(rubric: Dict, game_data: Dict) -> Dict:
    """Evaluate game against rubric using LLM"""
    client = get_client()
    if not client.is_available():
        print("❌ LLM not configured")
        return None
    
    # Format inputs
    rubric_json = json.dumps(rubric, indent=2)
    game_summary = format_game_summary(game_data)
    
    prompt = f"""You are an expert AoE IV coach. Evaluate this player's game against the provided rubric.

## Rubric
```json
{rubric_json}
```

## Game Data
{game_summary}

## Evaluation Task
Compare the player's game to the rubric and provide:
1. Overall adherence score (0-100)
2. Phase-by-phase analysis (what they did well, what deviated)
3. Specific timing comparisons vs benchmarks
4. Mistakes made (linked to rubric's common mistakes if applicable)
5. Actionable coaching feedback

Respond with JSON:
{{
  "adherence_score": 0-100,
  "overall_assessment": "brief summary",
  "phase_analysis": [
    {{
      "phase": "phase name",
      "score": 0-100,
      "what_went_well": ["..."],
      "deviations": ["..."],
      "benchmark_comparison": {{"benchmark": X, "actual": Y, "delta": Z}}
    }}
  ],
  "mistakes_observed": [
    {{
      "timestamp": "MM:SS or phase",
      "mistake": "description",
      "rubric_reference": "which common mistake this matches",
      "impact": "how this affected the game",
      "fix": "how to correct"
    }}
  ],
  "coaching_feedback": [
    "specific actionable advice"
  ]
}}
"""
    
    result = client.complete_with_retry(
        prompt=prompt,
        system_prompt="You are an expert AoE IV coach providing structured game evaluations.",
        temperature=0.4,
        json_mode=True
    )
    
    if not result['success']:
        print(f"Error: {result['error']}")
        return None
    
    try:
        return json.loads(result['content'])
    except json.JSONDecodeError as e:
        print(f"Failed to parse evaluation: {e}")
        return {"raw_response": result['content']}


def print_evaluation(evaluation: Dict, rubric: Dict, game_data: Dict):
    """Pretty print evaluation results"""
    player = game_data.get('player', {})
    
    print(f"\n{'='*60}")
    print(f"🎮 Game Evaluation: {player.get('name', 'Player')}")
    print(f"📋 Rubric: {rubric.get('title', 'Unknown')}")
    print(f"{'='*60}")
    
    score = evaluation.get('adherence_score', 'N/A')
    if isinstance(score, (int, float)):
        emoji = '🟢' if score >= 80 else '🟡' if score >= 60 else '🔴'
        print(f"\n{emoji} Overall Score: {score}/100")
    
    print(f"\n📊 Assessment:")
    print(f"  {evaluation.get('overall_assessment', 'No assessment provided')}")
    
    # Phase analysis
    phases = evaluation.get('phase_analysis', [])
    if phases:
        print(f"\n📈 Phase Analysis:")
        for phase in phases:
            print(f"\n  {phase.get('phase', 'Phase')}:")
            print(f"    Score: {phase.get('score', 'N/A')}/100")
            
            if phase.get('what_went_well'):
                print(f"    ✅ Good:")
                for item in phase['what_went_well']:
                    print(f"       • {item}")
            
            if phase.get('deviations'):
                print(f"    ⚠️  Deviations:")
                for item in phase['deviations']:
                    print(f"       • {item}")
    
    # Mistakes
    mistakes = evaluation.get('mistakes_observed', [])
    if mistakes:
        print(f"\n❌ Mistakes Observed:")
        for m in mistakes:
            print(f"\n  [{m.get('timestamp', '?')}] {m.get('mistake', '')}")
            if m.get('rubric_reference'):
                print(f"    📚 Matches: {m['rubric_reference']}")
            if m.get('impact'):
                print(f"    💥 Impact: {m['impact']}")
            if m.get('fix'):
                print(f"    🔧 Fix: {m['fix']}")
    
    # Coaching feedback
    feedback = evaluation.get('coaching_feedback', [])
    if feedback:
        print(f"\n💡 Coaching Feedback:")
        for item in feedback:
            print(f"  • {item}")
    
    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Evaluate game against rubric')
    parser.add_argument('--rubric', '-r', required=True, help='Rubric ID or name')
    parser.add_argument('--game-data', '-g', help='Path to game JSON file')
    parser.add_argument('--profile', '-p', help='Profile ID (for API fetch)')
    parser.add_argument('--game', help='Game ID (for API fetch)')
    parser.add_argument('--output', '-o', help='Save evaluation to file')
    parser.add_argument('--json', action='store_true', help='Output raw JSON')
    
    args = parser.parse_args()
    
    # Load rubric
    try:
        rubric = load_rubric(args.rubric)
        print(f"📋 Loaded rubric: {rubric.get('title', args.rubric)}")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print(f"\nAvailable rubrics:")
        # List available rubrics
        from list_rubrics import load_rubrics, print_table
        library_dir = Path(__file__).parent / 'rubric_library'
        rubrics = load_rubrics(library_dir)
        print_table(rubrics)
        sys.exit(1)
    
    # Load game data
    if args.game_data:
        game_data = load_game_data(args.game_data)
    elif args.profile and args.game:
        game_data = fetch_game_from_api(args.profile, args.game)
    else:
        print("❌ Provide either --game-data or both --profile and --game")
        sys.exit(1)
    
    print(f"🎮 Loaded game: {game_data.get('player', {}).get('name')} vs {game_data.get('opponent', {}).get('name')}")
    
    # Evaluate
    print(f"\n🤖 Evaluating against rubric...")
    evaluation = evaluate_against_rubric(rubric, game_data)
    
    if not evaluation:
        print("❌ Evaluation failed")
        sys.exit(1)
    
    # Output
    if args.json:
        print(json.dumps(evaluation, indent=2))
    else:
        print_evaluation(evaluation, rubric, game_data)
    
    # Save if requested
    if args.output:
        output_data = {
            'rubric': rubric.get('id'),
            'game': game_data.get('game', {}).get('game_id'),
            'evaluation': evaluation,
            'player': game_data.get('player', {}).get('name')
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"\n💾 Saved evaluation to: {args.output}")


if __name__ == '__main__':
    main()
