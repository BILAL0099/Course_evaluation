# AI Course Reviewer

Automated SCORM e-learning course testing system powered by FastAPI, Playwright browser automation, LangChain AI agents, and NLP tools.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [File Descriptions](#file-descriptions)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [How It Works](#how-it-works)
- [AI Agents](#ai-agents-langchain)
- [Issue Types](#issue-types)
- [Tech Stack](#tech-stack)
- [Requirements](#requirements)

---

## Overview

The AI Course Reviewer is an automated testing tool for SCORM-compliant e-learning courses. It simulates a learner navigating through a course while performing comprehensive quality checks including:

- Functional testing (navigation, buttons, media)
- Content quality analysis (spelling, grammar)
- AI-powered evaluation (clarity, accuracy, tone, accessibility)
- SCORM API compliance verification

---

## Features

| Feature | Description |
|---------|-------------|
| **SCORM Support** | Handles both SCORM 1.2 and SCORM 2004 packages |
| **Automated Navigation** | Navigates through slides like a human learner |
| **Functional Testing** | Checks buttons, navigation, media players, and timers |
| **Content Testing** | Spell checking and grammar analysis using NLP |
| **AI-Powered Analysis** | LangChain agents evaluate clarity, accuracy, tone, accessibility |
| **Fake LMS API** | Injects SCORM stub to simulate real LMS environment |
| **Screenshot Capture** | Takes screenshots of each slide for visual review |
| **Detailed Reports** | Generates JSON, HTML, and text summary reports |

---

## Project Structure

```
ai_course_reviewer/
│
├── main.py                         # Application entry point
├── config.py                       # Configuration settings
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── .env                            # Environment variables (create this)
│
├── endpoints/                      # API Layer
│   ├── __init__.py
│   └── review.py                   # REST API route handlers
│
└── src/                            # Source Code
    ├── __init__.py
    ├── schemas.py                  # Data models (Pydantic)
    │
    ├── scorm/                      # SCORM Package Handling
    │   ├── __init__.py
    │   ├── extractor.py            # ZIP extraction utility
    │   └── parser.py               # Manifest XML parser
    │
    ├── browser/                    # Browser Automation
    │   ├── __init__.py
    │   ├── manager.py              # Playwright browser controller
    │   └── scorm_stub.js           # Fake LMS SCORM API
    │
    ├── agents/                     # Testing Agents
    │   ├── __init__.py
    │   ├── orchestrator.py         # Main review coordinator
    │   ├── functional.py           # Functional testing agent
    │   ├── content.py              # Content quality agent
    │   └── ai_agents.py            # LangChain AI agents
    │
    └── reports/                    # Report Generation
        ├── __init__.py
        └── generator.py            # Report generator
```

---

## File Descriptions

### Root Files

| File | Description |
|------|-------------|
| `main.py` | FastAPI application entry point. Creates the app instance, configures middleware (CORS), mounts static directories, and includes API routers. Run this to start the server. |
| `config.py` | Centralized configuration using Pydantic Settings. Contains all adjustable parameters for browser, review process, AI agents, and file storage paths. Reads from `.env` file. |
| `requirements.txt` | List of Python package dependencies with pinned versions. |
| `.env` | Environment variables file (you create this). Contains API keys and configuration overrides. |

### Endpoints (`endpoints/`)

| File | Description |
|------|-------------|
| `review.py` | REST API route handlers for the review workflow. Contains 4 main endpoints: upload SCORM package, start review, check status, and get report. Manages in-memory storage of review state. |

### Schemas (`src/schemas.py`)

| Model | Purpose |
|-------|---------|
| `ReviewStatus` | Enum for review states (pending, extracting, parsing, reviewing, completed, failed) |
| `IssueType` | Enum for all issue categories (navigation, spelling, clarity, etc.) |
| `IssueSeverity` | Enum for severity levels (info, warning, error, critical) |
| `Issue` | Single issue found during review |
| `SlideResult` | Complete results for one slide |
| `SCORMManifest` | Parsed manifest data |
| `ReviewProgress` | Current review progress |
| `ReviewReport` | Final comprehensive report |
| `AIAnalysisResult` | Result from a single AI agent |
| `SlideAIAnalysis` | Combined AI analysis for a slide |

### SCORM Handling (`src/scorm/`)

| File | Description |
|------|-------------|
| `extractor.py` | **SCORMExtractor class** - Handles ZIP file extraction. Validates that the package contains `imsmanifest.xml`. Supports packages with manifest in root or one level deep. |
| `parser.py` | **SCORMParser class** - Parses `imsmanifest.xml` to extract course metadata. Identifies launch file, course title, SCORM version (1.2 or 2004), resources, and organization structure. |

### Browser Automation (`src/browser/`)

| File | Description |
|------|-------------|
| `manager.py` | **BrowserManager class** - Controls Playwright Chromium browser. Handles navigation, screenshots, element interaction, keyboard input, and page content extraction. Injects SCORM stub on every page load. |
| `scorm_stub.js` | JavaScript file injected into course pages. Creates fake `window.API` (SCORM 1.2) and `window.API_1484_11` (SCORM 2004) objects. Tracks all SCORM calls in `window.__SCORM__` for inspection. |

### Testing Agents (`src/agents/`)

| File | Description |
|------|-------------|
| `orchestrator.py` | **ReviewOrchestrator class** - Main controller that coordinates the entire review process. Manages browser lifecycle, navigates through slides, invokes agents, handles stuck detection, and generates final report. |
| `functional.py` | **FunctionalAgent class** - Tests functional aspects of each slide: navigation buttons, interactive elements, media players (audio/video), timers, and SCORM API calls. Attempts navigation using buttons and keyboard. |
| `content.py` | **ContentAgent class** - Analyzes text content quality. Uses pyspellchecker for spelling, language-tool-python for grammar, and coordinates with AI agents for advanced analysis. |
| `ai_agents.py` | **LangChain AI Agents** - Contains 5 specialized AI agents (Clarity, Accuracy, Tone, Accessibility, Structure) and an AIAgentOrchestrator that coordinates them. Each agent uses structured prompts to analyze content and return JSON-formatted results. |

### Reports (`src/reports/`)

| File | Description |
|------|-------------|
| `generator.py` | **ReportGenerator class** - Generates reports in multiple formats: JSON (machine-readable), HTML (visual with styling), and plain text summary. Includes issue statistics, recommendations, and slide-by-slide details. |

---

## Installation

### 1. Clone/Navigate to Project

```bash
cd ai_course_reviewer
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browser

```bash
playwright install chromium
```

### 5. Create Environment File

Create a `.env` file in the project root:

```env
# Required for AI features
OPENAI_API_KEY=sk-your-openai-key-here

# Or use Anthropic instead
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 6. Start the Server

```bash
python main.py

# Or with auto-reload for development
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

---

## Configuration

All settings can be configured via `config.py` or overridden in `.env` file.

### General Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `DEBUG` | `true` | Enable debug mode |
| `HEADLESS` | `true` | Run browser without GUI |
| `BROWSER_TIMEOUT` | `30000` | Browser operation timeout (ms) |
| `MAX_SLIDES` | `500` | Maximum slides to review |
| `SLIDE_WAIT_TIME` | `2.0` | Seconds to wait between slides |
| `STUCK_TIMEOUT` | `10.0` | Seconds before navigation considered stuck |
| `SKIP_KEY_COMBO` | `Control+Shift+S` | Keyboard shortcut to skip stuck slides |

### AI Agent Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_AI_AGENTS` | `true` | Enable/disable AI analysis |
| `LLM_PROVIDER` | `openai` | LLM provider (`openai` or `anthropic`) |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-3-haiku-20240307` | Anthropic model name |
| `AI_CLARITY_CHECK` | `true` | Enable clarity analysis |
| `AI_ACCURACY_CHECK` | `true` | Enable accuracy analysis |
| `AI_TONE_CHECK` | `true` | Enable tone analysis |
| `AI_ACCESSIBILITY_CHECK` | `true` | Enable accessibility analysis |
| `AI_MAX_TOKENS` | `2000` | Max tokens per AI request |
| `AI_TEMPERATURE` | `0.1` | LLM temperature (lower = more focused) |

### Example `.env` File

```env
# General
DEBUG=true
HEADLESS=true
MAX_SLIDES=100

# AI Configuration
ENABLE_AI_AGENTS=true
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
AI_TEMPERATURE=0.1
```

---

## API Endpoints

### Base URL: `http://localhost:8000`

### 1. Upload SCORM Package

Upload a SCORM ZIP file for review.

```http
POST /api/upload
Content-Type: multipart/form-data
```

**Request Body:**
- `file`: SCORM ZIP file

**Response:**
```json
{
  "review_id": "a1b2c3d4",
  "filename": "my-course.zip",
  "file_size": 5242880,
  "message": "Upload successful. Use POST /api/start/{review_id} to begin review."
}
```

### 2. Start Review

Begin the automated review process.

```http
POST /api/start/{review_id}
```

**Response:**
```json
{
  "review_id": "a1b2c3d4",
  "message": "Review started. Use GET /api/status/{review_id} to check progress."
}
```

### 3. Check Status

Get current review progress.

```http
GET /api/status/{review_id}
```

**Response:**
```json
{
  "review_id": "a1b2c3d4",
  "status": "reviewing",
  "progress": {
    "review_id": "a1b2c3d4",
    "status": "reviewing",
    "current_slide": 12,
    "total_slides": 12,
    "issues_found": 7,
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": null,
    "error_message": null
  }
}
```

### 4. Get Report

Retrieve the complete review report (only available after completion).

```http
GET /api/report/{review_id}
```

**Response:** Full `ReviewReport` JSON object with slide-by-slide analysis.

### 5. Delete Review

Remove a review and its associated files.

```http
DELETE /api/review/{review_id}
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        REVIEW WORKFLOW                          │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
    │  UPLOAD  │────▶│ EXTRACT  │────▶│  PARSE   │────▶│  REVIEW  │
    └──────────┘     └──────────┘     └──────────┘     └──────────┘
         │                │                │                │
    Upload ZIP       Unzip to        Parse manifest    Load in browser
    via API          temp folder     (imsmanifest.xml) with SCORM stub
                                                             │
                                                             ▼
                                     ┌─────────────────────────────┐
                                     │     FOR EACH SLIDE:        │
                                     │  ┌─────────────────────┐   │
                                     │  │ 1. Take screenshot  │   │
                                     │  │ 2. Functional tests │   │
                                     │  │ 3. Content analysis │   │
                                     │  │ 4. AI evaluation    │   │
                                     │  │ 5. Navigate next    │   │
                                     │  └─────────────────────┘   │
                                     │         │                  │
                                     │    If stuck ──▶ Use skip   │
                                     │         │         key      │
                                     │         ▼                  │
                                     │  Course complete?          │
                                     └─────────────────────────────┘
                                                  │
                                                  ▼
                                          ┌──────────┐
                                          │  REPORT  │
                                          └──────────┘
                                          Generate JSON,
                                          HTML, and text
                                          reports
```

### Step-by-Step Process

1. **Upload** - User uploads SCORM ZIP via POST /api/upload
2. **Extract** - ZIP is extracted, validated for `imsmanifest.xml`
3. **Parse** - Manifest is parsed to find launch file and course metadata
4. **Initialize** - Browser starts, SCORM stub is injected
5. **Review Loop** - For each slide:
   - Screenshot captured
   - Functional agent tests navigation, buttons, media
   - Content agent checks spelling, grammar
   - AI agents analyze clarity, accuracy, tone, accessibility
   - Navigate to next slide (button click or keyboard)
   - If stuck, use skip key and log issue
6. **Complete** - When course ends or max slides reached
7. **Report** - Generate comprehensive report with all findings

---

## AI Agents (LangChain)

The system uses specialized LangChain AI agents for intelligent content analysis.

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AIAgentOrchestrator                          │
│  Coordinates all agents, aggregates results, calculates scores  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ ClarityAgent  │   │ AccuracyAgent │   │   ToneAgent   │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐
│Accessibility  │   │StructureAgent │
│    Agent      │   │               │
└───────────────┘   └───────────────┘
```

### Agent Descriptions

| Agent | Purpose | Checks For |
|-------|---------|------------|
| **ClarityAgent** | Readability analysis | Complex sentences, jargon, unclear explanations, vocabulary level |
| **AccuracyAgent** | Factual verification | Internal contradictions, outdated info, logical errors, unverified claims |
| **ToneAgent** | Tone evaluation | Professional language, inclusivity, engagement, audience fit |
| **AccessibilityAgent** | Accessibility check | Plain language, undefined acronyms, color-only meaning, sensory assumptions |
| **StructureAgent** | Organization analysis | Logical flow, chunking, transitions, information hierarchy |

### AI Output Format

Each agent returns structured JSON:

```json
{
  "score": 85,
  "summary": "Content is mostly clear with minor issues",
  "issues": [
    {
      "issue_type": "clarity",
      "severity": "warning",
      "message": "Sentence too complex",
      "suggestion": "Break into shorter sentences",
      "location": "paragraph 2"
    }
  ],
  "suggestions": [
    "Consider adding a glossary for technical terms"
  ]
}
```

---

## Issue Types

### Functional Issues

| Type | Description | Severity |
|------|-------------|----------|
| `NAVIGATION` | Cannot navigate between slides | Warning - Critical |
| `BUTTON` | Button doesn't work or lacks accessibility | Warning - Error |
| `MEDIA` | Audio/video errors or missing sources | Error |
| `TIMER` | Timer-related problems | Info - Warning |
| `SCORM_ERROR` | SCORM API communication errors | Error - Critical |
| `STUCK` | Required skip key to proceed | Warning - Critical |

### Content Issues (NLP)

| Type | Description | Severity |
|------|-------------|----------|
| `SPELLING` | Misspelled words | Warning |
| `GRAMMAR` | Grammar errors | Warning - Error |

### AI-Detected Issues

| Type | Description | Severity |
|------|-------------|----------|
| `CLARITY` | Unclear or confusing content | Info - Error |
| `ACCURACY` | Factual inconsistencies | Warning - Critical |
| `TONE` | Inappropriate tone | Warning - Error |
| `CONSISTENCY` | Inconsistent terminology | Info - Warning |
| `READABILITY` | Hard to read | Warning |
| `STRUCTURE` | Poor organization | Warning |
| `ENGAGEMENT` | Low engagement quality | Info |
| `ACCESSIBILITY` | Accessibility concerns | Warning - Error |

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Web Framework** | FastAPI | REST API server |
| **Browser Automation** | Playwright | Headless browser control |
| **AI/LLM** | LangChain + OpenAI/Anthropic | Intelligent content analysis |
| **Spell Check** | pyspellchecker | Spelling verification |
| **Grammar Check** | language-tool-python | Grammar analysis |
| **XML Parsing** | lxml | SCORM manifest parsing |
| **Data Models** | Pydantic | Request/response validation |
| **Async** | asyncio | Non-blocking operations |

---

## Requirements

### System Requirements

- **Python**: 3.10 or higher
- **RAM**: 4GB minimum (8GB recommended)
- **Disk**: 1GB free space for extracted courses
- **Network**: Required for AI features (API calls)

### Dependencies

See `requirements.txt` for complete list. Key packages:

```
fastapi==0.109.0
playwright==1.41.0
langchain==0.1.9
langchain-openai==0.0.6
pyspellchecker==0.8.1
language-tool-python==2.7.1
lxml==5.1.0
```

---

## License

MIT License

---

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt
playwright install chromium

# 2. Configure
echo "OPENAI_API_KEY=sk-your-key" > .env

# 3. Run
python main.py

# 4. Test
curl -X POST -F "file=@course.zip" http://localhost:8000/api/upload
```
