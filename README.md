# YouTube Tutorial Rubric Extractor

Extract coaching rubrics from AoE IV YouTube tutorials and use them to evaluate real games.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys
export OPENAI_API_KEY="your-key"  # or ZAI_API_KEY

# Extract rubric from YouTube video
python extract_rubric.py --url "https://youtube.com/watch?v=..." --title "Fast Castle Tutorial"

# List all extracted rubrics
python list_rubrics.py

# Evaluate a game against rubrics
python evaluate_game.py --rubric fast_castle --game-data game.json
```

## How It Works

1. **Download** YouTube transcript (auto-generated or manual captions)
2. **Chunk & Summarize** Split long tutorials into logical sections
3. **Extract Rubric** Use LLM to identify:
   - Key decision points
   - Success criteria
   - Common mistakes
   - Benchmark timings
4. **Store** Structured rubric in JSON format
5. **Evaluate** Compare real game data against rubric criteria

## Rubric Format

```json
{
  "id": "fast_castle_hera",
  "title": "Hera's Fast Castle Guide",
  "source": "https://youtube.com/watch?v=...",
  "difficulty": "intermediate",
  "archetype": "fast_castle_boom",
  "civilizations": ["english", "french", "hre"],
  "map_types": ["open", "closed"],
  
  "phases": [
    {
      "name": "Dark Age",
      "duration_range": [240, 330],
      "key_actions": [
        {
          "action": "6 sheep → 4 wood → berries → farms",
          "timing": "standard",
          "importance": "critical"
        }
      ],
      "success_criteria": [
        "No TC idle time before Feudal click",
        "Scout finds 8 sheep minimum"
      ],
      "common_mistakes": [
        {
          "mistake": "Late 2nd lumber camp",
          "consequence": "Wood shortage delays buildings",
          "fix": "Send 4th wood vill when 200 wood banked"
        }
      ]
    }
  ],
  
  "benchmarks": {
    "feudal_age": 300,
    "castle_age": 780,
    "second_tc": 660,
    "villagers_at_castle": 35
  },
  
  "decision_points": [
    {
      "trigger": "opponent_early_pressure_detected",
      "adaptation": "add_stable_or_archery",
      "alternative": "stone_wall_defensive"
    }
  ]
}
```

## Directory Structure

```
youtube-rubric-extractor/
├── extract_rubric.py       # Main extraction script
├── evaluate_game.py        # Game evaluation against rubrics
├── list_rubrics.py         # List available rubrics
├── rubric_library/         # Stored rubrics
│   ├── fast_castle_hera.json
│   └── scout_rush_viper.json
├── utils/
│   ├── youtube.py          # YouTube transcript download
│   ├── llm_client.py       # LLM API wrapper
│   └── rubric_parser.py    # Parse LLM output to structured rubric
└── prompts/
    └── extract_rubric.txt  # LLM prompt template
```

## Future Features

- [ ] Batch process playlist of tutorials
- [ ] Rubric versioning (per patch/game version)
- [ ] Merge similar rubrics from multiple sources
- [ ] Visual rubric builder UI
- [ ] Community rubric sharing

---
*MVP created: February 4, 2026*
