# Car Coach

Your personal AI car build assistant. Knows your car, your goals, and what's next for your build.

## Setup

```bash
cd car_coach

# Install dependencies
pip install -r requirements.txt

# Copy the example profile and edit it
cp profiles/my_car.json.example profiles/my_car.json
# Edit profiles/my_car.json with your car details

# Set your API keys (optional but recommended for web search)
export TAVILY_API_KEY=your_key_here   # Free at https://tavily.com
# OR
export SERPER_API_KEY=your_key_here   # Free at https://serpapi.com
```

## Running

```bash
python car_coach.py
```

You'll see something like:
```
🚗 Car Coach — Your Build Assistant
============================================
📋 Loaded: 2018 Subaru WRX STI
   Mods: COBB AccessPort Stage 2 Tune, Megan Racing Catback Exhaust, Group N Bilstein HDs + Cobra Springs

You:
```

## Features

- **Knows your car** — reads from `profiles/my_car.json`
- **Remembers your build** — tracks completed mods and milestones
- **Web search** — looks up current prices and fitment when needed
- **Build order logic** — knows what has to come before what
- **Conflict detection** — flags bad combos (e.g., turning up boost before upgrading the intercooler)

## Car Profile

Edit `profiles/my_car.json` with your specs:

```json
{
  "year": "2019",
  "make": "Toyota",
  "model": "GR86",
  "trim": "Premium",
  "engine": "2.4L Boxer",
  "drivetrain": "RWD",
  "currentMods": ["Coilovers", "Wheels"],
  "goals": "Street + occasional track",
  "budget": "$5k",
  "focus": "handling"
}
```

## Web Search

Set `TAVILY_API_KEY` for real-time part searches. Without it, the app still works but won't have current prices.

Get a free key at [tavily.com](https://tavily.com) — 1000 searches/month free.

## Model Configuration

Edit `model_loader.py` to change the AI model:

- **Local (free):** Ollama with `qwen3:14b-q8_0`
- **Cheap cloud:** OpenRouter with `moonshotai/kimi-k2.5`
- **Best quality:** Anthropic Claude

## Customizing

- `prompts/car_knowledge.py` — change how the AI behaves
- `memory/build_memory.py` — change how build history is tracked
- `search/web_search.py` — add new search backends

## Example Session

```
You: what should I do next for more power?

Car Coach: You've got the AP Stage 2 tune and catback already — solid base.
For more power on a streetable daily, the logical next step is an intercooler.
Your current setup is hitting heat soak limits in summer.
Top picks for your 2018 STI:
- Grimmspeed High Flow Crossover Intercooler ($600)
- Processings FF Intercooler ($750)
Both fit your model year direct. The Grimmspeed is easier install if you're doing it yourself.

You: what's the estimated cost including install?

Car Coach: Grimmspeed kit runs $600 parts + $200-400 labor if you're not doing it yourself.
You're looking at $800-1000 total. The kit includes everything you need — no additional parts required.
```

## Troubleshooting

**"Ollama error: connection refused"**
→ Start Ollama: `ollama serve`

**"OpenAI API error"**
→ Check your `OPENAI_API_KEY` environment variable

**No car profile loaded**
→ Copy `profiles/my_car.json.example` to `profiles/my_car.json` and fill it in