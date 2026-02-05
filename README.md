# AI Course Reviewer

Automated SCORM e-learning course testing system using FastAPI, Playwright, and LangChain AI agents.

---

## What This Project Does

This tool automatically tests SCORM e-learning courses by:
- Uploading and extracting SCORM ZIP packages
- Opening courses in a headless browser with a fake LMS
- Navigating through all slides automatically
- Running functional tests (buttons, navigation, media)
- Running content checks (spelling, grammar)
- Using AI agents to evaluate content quality
- Generating detailed reports

---

## Tech Stack

- **FastAPI** - REST API framework
- **Playwright** - Browser automation
- **LangChain** - AI agent framework
- **OpenAI / Anthropic** - LLM providers
- **pyspellchecker** - Spelling checks
- **language-tool-python** - Grammar checks
- **lxml** - XML parsing

---

## Project Structure

```
ai_course_reviewer/
│
├── main.py                 # FastAPI app entry point
├── config.py               # Settings and configuration
├── requirements.txt        # Python dependencies
├── .env                    # Secret keys
├── .gitignore              # Git ignore rules
│
├── endpoints/
│   └── review.py           # API routes 
│
└── src/
    ├── schemas.py          # Pydantic data models
    │
    ├── scorm/
    │   ├── extractor.py    # ZIP extraction
    │   └── parser.py       # Manifest XML parsing
    │
    ├── browser/
    │   ├── manager.py      # Playwright browser control
    │   └── scorm_stub.js   # Fake LMS SCORM API
    │
    ├── agents/
    │   ├── orchestrator.py # Main review controller
    │   ├── functional.py   # Functional testing agent
    │   ├── content.py      # Content quality agent
    │   └── ai_agents.py    # LangChain AI agents
    │
    └── reports/
        └── generator.py    # Report generation
```

---

## File Descriptions

### Root Files

| File | Purpose |
|------|---------|
| `main.py` | Creates FastAPI app, sets up routes and middleware |
| `config.py` | All configuration settings (browser, AI, paths) |
| `requirements.txt` | Python package dependencies |
| `.env` | Environment variables (API keys) - you create this |

### API Layer (`endpoints/`)

| File | Purpose |
|------|---------|
| `review.py` | REST endpoints: POST /upload, POST /start, GET /status, GET /report |

### Data Models (`src/`)

| File | Purpose |
|------|---------|
| `schemas.py` | Pydantic models for requests, responses, and internal data |

### SCORM Handling (`src/scorm/`)

| File | Purpose |
|------|---------|
| `extractor.py` | Extracts SCORM ZIP files, validates manifest exists |
| `parser.py` | Parses imsmanifest.xml to find launch file and course info |

### Browser (`src/browser/`)

| File | Purpose |
|------|---------|
| `manager.py` | Controls headless browser (navigate, click, screenshot) |
| `scorm_stub.js` | JavaScript injected to fake LMS API (window.API) |

### Agents (`src/agents/`)

| File | Purpose |
|------|---------|
| `orchestrator.py` | Main controller - coordinates entire review process |
| `functional.py` | Tests buttons, navigation, media, timers |
| `content.py` | Checks spelling, grammar, integrates AI agents |
| `ai_agents.py` | LangChain agents: Clarity, Accuracy, Tone, Accessibility, Structure |

### Reports (`src/reports/`)

| File | Purpose |
|------|---------|
| `generator.py` | Generates JSON, HTML, and text reports |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload SCORM ZIP file |
| POST | `/api/start/{id}` | Start review process |
| GET | `/api/status/{id}` | Check review progress |
| GET | `/api/report/{id}` | Get final report |

---
## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install browser
playwright install chromium

# Create .env file with your API key
echo "OPENAI_API_KEY=sk-your-key" > .env

# Run server
python main.py
```


---

## License

MIT License
