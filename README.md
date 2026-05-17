# Car Coach

Your personal AI car build assistant. Knows your car, your goals, and what's next for your build.

## Quick Start

```bash
git clone https://github.com/notcranky/car-coach
cd car-coach
cp profiles/my_car.json.example profiles/my_car.json
# Edit profiles/my_car.json with your car specs

pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open **http://localhost:8501** in your browser.

That's it — a web UI running on your PC that you can chat with.

## Running Options

### Terminal (no UI)
```bash
python car_coach.py
```
Simple CLI — chat in the terminal.

### Web UI (Streamlit)
```bash
streamlit run streamlit_app.py
```
Opens a browser window with a chat interface. Better for long conversations, lets you scroll back, has a settings sidebar.

### Both
Run `streamlit_app.py` in one terminal window and use the web UI. You can have both running at the same time.

## Features

- **Knows your car** — reads from `profiles/my_car.json`
- **Remembers your build** — tracks completed mods and milestones
- **Web search** — looks up current prices and fitment (enable in sidebar)
- **Build order logic** — knows what has to come before what
- **Conflict detection** — flags bad combos (e.g., turning up boost before upgrading the intercooler)

## Car Profile

Edit `profiles/my_car.json`:

```json
{
  "year": "2018",
  "make": "Subaru",
  "model": "WRX",
  "trim": "STI",
  "engine": "EJ257 2.5L Turbo",
  "drivetrain": "AWD",
  "transmission": "6-speed manual",
  "mileage": "41,200",
  "currentMods": [
    "COBB AccessPort Stage 2 Tune",
    "Megan Racing Catback Exhaust",
    "Group N Bilstein HDs + Cobra Springs"
  ],
  "goals": "Stage 2 power, proper suspension, keep it streetable",
  "budget": "$5k-$10k",
  "focus": "performance"
}
```

## Web Search

Toggle "Enable web search" in the sidebar. Requires a `TAVILY_API_KEY` or `SERPER_API_KEY` environment variable.

Free Tavily key: https://tavily.com (1,000 searches/month)

## Hosting on a VPS (for outside access)

### Option 1 — Streamlit Cloud (free, 1 app)
1. Push to GitHub
2. Go to https://streamlit.io/cloud
3. Connect your repo and deploy

### Option 2 — Run on a VPS (your own server)
```bash
# On the VPS
pip install -r requirements.txt
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501

# Access at http://your_vps_ip:8501
```

### Option 3 — Run behind a domain
```bash
# Use nginx as a reverse proxy to port 80/443
# Point domain at your VPS
```

## Model Configuration

Edit `model_loader.py` to switch AI providers:

```python
CONFIG = {
    "provider": "ollama",      # Local, free
    # OR
    "provider": "openai",      # Cloud (OpenRouter, Groq)
    # OR
    "provider": "anthropic",   # Claude
}
```

**Ollama (default, free):** Requires `ollama serve` running locally. Model: `qwen3:14b-q8_0`

**OpenAI-compatible:** Set `OPENAI_API_KEY` env var. Uses `moonshotai/kimi-k2.5` by default.

**Anthropic Claude:** Set `ANTHROPIC_API_KEY` env var.

## Customizing

- `prompts/car_knowledge.py` — change how the AI behaves
- `memory/build_memory.py` — change how build history is tracked
- `search/web_search.py` — add new search backends
- `streamlit_app.py` — change the web UI

## Project Structure

```
car_coach/
├── car_coach.py          # Terminal app
├── streamlit_app.py      # Web UI (run with streamlit)
├── model_loader.py        # AI model configuration
├── profiles/
│   └── my_car.json       # Your car specs
├── prompts/
│   └── car_knowledge.py  # AI behavior prompt
├── memory/
│   └── build_memory.py   # Build history tracker
└── search/
    └── web_search.py     # Web search integration
```