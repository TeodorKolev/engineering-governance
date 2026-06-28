# Engineering Governance Agent

An AI-powered CTO governance system built with [Google ADK](https://adk.dev/). It runs a sequential pipeline of five specialist AI agents that review engineering changes, then synthesises their findings into a binding `GovernanceDecision`.

## Architecture

```
User request (PR URL or Jira ticket)
        │
        ▼
┌─────────────────────────────────────────────────┐
│              cto_orchestrator                   │
│           (SequentialAgent)                     │
│                                                 │
│  1. security_agent   → SecurityAssessment       │
│  2. architecture_agent → ArchitectureReview     │
│  3. delivery_agent   → DeliveryPlan             │
│  4. cost_agent       → CostAnalysis             │
│  5. evaluation_agent → EvaluationReport         │
│  6. cto_synthesizer  → GovernanceDecision       │
└─────────────────────────────────────────────────┘
```

Each specialist writes its structured output to session state. The `cto_synthesizer` reads all five and produces a final `GovernanceDecision` with an `overall_recommendation` of `APPROVE`, `APPROVE_WITH_CONDITIONS`, `DEFER`, or `REJECT`.

## Agents

| Agent | Tools | Output |
|---|---|---|
| `security_agent` | GitHub (PR + files) | `SecurityAssessment` |
| `architecture_agent` | GitHub (PR + files) | `ArchitectureReview` |
| `delivery_agent` | GitHub (PR + reviews + status) | `DeliveryPlan` |
| `cost_agent` | None (uses built-in AWS pricing knowledge) | `CostAnalysis` |
| `evaluation_agent` | GitHub (PR + reviews + status + files) | `EvaluationReport` |
| `cto_synthesizer` | `request_input` (human-in-the-loop) | `GovernanceDecision` |

## Usage

Send any of the following to the agent in the playground UI:

```
Review https://github.com/owner/repo/pull/42
```
```
KAN-1: Add Redis caching to the user-service
```
```
Run governance for PR #42 in owner/repo
```

The system detects change requests by keyword (`pr`, `pull`, `github`, `review`, `deploy`, …) and by Jira-style ticket IDs (`[A-Z]+-\d+`). Anything else is treated as a general chat query and skips the specialist pipeline.

## Setup

### Requirements

- Python 3.11+
- Node.js (for GitHub MCP server via `npx`)
- `uv` package manager
- A [Google AI Studio API key](https://aistudio.google.com/apikey) (starts with `AIza`)

### Install

```bash
agents-cli install
```

### Configure

Copy `app/.env.example` to `app/.env` and fill in:

```env
# Required
GEMINI_API_KEY=AIza...          # Google AI Studio key (NOT a Vertex AI key)
GOOGLE_GENAI_USE_VERTEXAI=false
GEMINI_MODEL=gemini-2.0-flash

# GitHub (for PR reviews)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...

# Free-tier throttle (seconds between agents). Set to 0 on paid tiers.
INTER_AGENT_DELAY_SECONDS=12
```

### Run

```bash
agents-cli playground
```

Opens the ADK dev UI at `http://localhost:8080`.

## Rate Limit Notes

This project runs 6 sequential LLM calls per governance review. On the Gemini API free tier:

| Key type | RPM | TPM | RPD |
|---|---|---|---|
| AI Studio (`AIza...`) | 15 | 1M | 1,500 |
| Vertex AI (`AQ...`) | 5 | 250k | 20 |

Always use an AI Studio key. The `INTER_AGENT_DELAY_SECONDS` env var (default `12`) spreads calls across the 1-minute TPM window to avoid 429 errors on the free tier.

## Project Structure

```
eng-governance/
├── app/
│   ├── agent.py                  # Root orchestrator + patches + callbacks
│   ├── agents/
│   │   ├── security_agent.py
│   │   ├── architecture_agent.py
│   │   ├── delivery_agent.py
│   │   ├── cost_agent.py
│   │   ├── evaluation_agent.py
│   │   └── _throttle.py          # Inter-agent rate-limit callback
│   ├── schemas/                  # Pydantic output schemas
│   ├── tools/
│   │   └── github_tools.py       # GitHub MCP toolset factory
│   └── .env                      # Local config (not committed)
├── tests/
├── GEMINI.md
└── README.md
```

## Commands

| Command | Description |
|---|---|
| `agents-cli playground` | Launch local dev UI |
| `agents-cli lint` | Run code quality checks |
| `agents-cli eval` | Evaluate agent behaviour |
| `uv run pytest tests/unit tests/integration` | Run tests |
| `agents-cli deploy` | Deploy to Cloud Run |
