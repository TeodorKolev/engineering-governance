# Engineering Governance Agent

An AI-powered CTO governance system built with [Google ADK](https://adk.dev/). It runs a sequential pipeline of five specialist AI agents that review engineering changes, then synthesises their findings into a binding `GovernanceDecision`.

---

## Architecture

```
User request (GitHub PR URL or change description)
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

Each specialist writes its structured JSON output to session state via `output_key`. The `cto_synthesizer` reads all five outputs and produces a final `GovernanceDecision` with an `overall_recommendation` of `APPROVE`, `APPROVE_WITH_CONDITIONS`, `DEFER`, or `REJECT`.

---

## Agents

### 1. `security_agent`
**Role:** Senior Security Engineer  
**Tools:** `get_pull_request`, `get_pull_request_files`  
**Output schema:** `SecurityAssessment`

Fetches the PR title/description and the list of changed files, then identifies security risks. Checks for: hardcoded secrets, injection vulnerabilities (SQL/command/XSS), broken access control, insecure dependencies (CVEs), and compliance implications (SOC2, GDPR, PCI-DSS).

Severity levels: `CRITICAL` → `HIGH` → `MEDIUM` → `LOW`. Sets `requires_human_approval = True` if `overall_risk` is `HIGH` or `CRITICAL`, or if any individual finding is `CRITICAL`.

If no GitHub PR URL is provided, returns `overall_risk = LOW` with a note that a PR link is needed for a full review.

---

### 2. `architecture_agent`
**Role:** Principal Software Architect  
**Tools:** `get_pull_request`, `get_pull_request_files`  
**Output schema:** `ArchitectureReview`

Inspects the changed file list and PR description to assess design quality: coupling, separation of concerns, missing abstractions, scalability bottlenecks (N+1 queries, missing caching, synchronous fan-out), and new dependency risks.

Verdicts: `APPROVED` / `APPROVED_WITH_CONCERNS` / `NEEDS_REWORK`. Sets `requires_human_approval = True` if verdict is `NEEDS_REWORK` or any concern is `HIGH` severity.

If no GitHub PR URL is provided, returns `APPROVED` with a note that a PR link is needed.

---

### 3. `delivery_agent`
**Role:** Engineering Delivery Manager  
**Tools:** `get_pull_request`, `get_pull_request_reviews`, `get_pull_request_status`  
**Output schema:** `DeliveryPlan`

Checks whether the PR is ready to ship: review approvals, CI check status, merge conflicts, and mergeable state. Identifies delivery risks such as deadline conflicts, resource contention, dependency blockers, and rollback complexity.

Feasibility: `ON_TRACK` / `AT_RISK` / `BLOCKED`. Sets `requires_human_approval = True` if `BLOCKED` or any risk has `HIGH` probability.

If no GitHub PR URL is provided, returns `ON_TRACK` with a note that a PR link is needed.

---

### 4. `cost_agent`
**Role:** Cloud FinOps Engineer  
**Tools:** None  
**Output schema:** `CostAnalysis`

Works entirely from the change description and built-in cloud pricing knowledge. Identifies AWS resources being added or scaled (EC2, RDS, S3, Lambda, EKS), estimates the monthly cost delta, and classifies impact: `NEGLIGIBLE` (<$50) / `LOW` ($50–$500) / `MEDIUM` ($500–$5k) / `HIGH` ($5k–$50k) / `CRITICAL` (>$50k).

Sets `requires_human_approval = True` if impact is `HIGH` or `CRITICAL`. If the change has no infrastructure component, returns `NEGLIGIBLE` and explains why.

---

### 5. `evaluation_agent`
**Role:** Quality Engineering  
**Tools:** `get_pull_request`, `get_pull_request_reviews`, `get_pull_request_status`, `get_pull_request_files`  
**Output schema:** `EvaluationReport`

Assesses code quality and release readiness: PR review status (approved / changes requested / not reviewed), CI pipeline pass/fail, and test coverage gaps (missing unit/integration/e2e tests inferred from changed file paths).

Quality gate: `PASS` / `CONDITIONAL_PASS` / `FAIL`. Sets `requires_human_approval = True` if gate is `FAIL` or review status is `NOT_REVIEWED` / `CHANGES_REQUESTED`.

---

### 6. `cto_synthesizer`
**Role:** Chief Technology Officer  
**Tools:** `request_input` (human-in-the-loop gate)  
**Output schema:** `GovernanceDecision`

Reads all five specialist assessments from session state, normalises their risk levels to a shared 4-level scale (`LOW` / `MEDIUM` / `HIGH` / `CRITICAL`), and applies deterministic recommendation rules:

| Rule | Condition | Recommendation |
|---|---|---|
| 1 | Any CRITICAL security finding | `REJECT` |
| 2 | Delivery BLOCKED or budget unavailable | `DEFER` |
| 3 | HIGH security/architecture risk, fixable CI failure | `APPROVE_WITH_CONDITIONS` |
| 4 | All risks LOW or MEDIUM | `APPROVE` |

If any specialist set `requires_human_approval = True`, the synthesizer calls `request_input` to pause and collect a named human decision before producing the final output.

---

## Usage

Send any of the following to the agent in the playground UI:

```
Review https://github.com/owner/repo/pull/42
```
```
KAN-1: Add Redis caching to the user-service API
```
```
We're migrating from db.t3.micro to db.r6g.4xlarge for the holiday season
```

The system detects change requests by keyword (`pr`, `pull`, `github`, `review`, `deploy`, …) and by ticket IDs matching `[A-Z]+-\d+` (e.g. `KAN-1`). Anything else is treated as a general chat query and skips the specialist pipeline.

**Tip:** For the richest output, always include a GitHub PR URL. Without it, agents can still assess cost and architecture from the description, but security and delivery checks will return minimal results.

---

## Setup

### Requirements

- Python 3.11+
- Node.js 22 LTS (for the GitHub MCP server — installed automatically in Docker)
- `uv` package manager
- A [Google AI Studio API key](https://aistudio.google.com/apikey) (starts with `AIza`)

### Install

```bash
agents-cli install
```

This installs Python dependencies via `uv` and pre-fetches the GitHub MCP npm package into `node_modules/` so the server starts without hitting the npm registry at runtime.

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

---

## ADK Dev UI Guide

The playground UI (`agents-cli playground`) has four main sections:

### Chat panel (left)
Send your change request here. The agent responds with the final `GovernanceDecision` JSON once all six agents have completed. Because agents run sequentially with a 12-second inter-agent delay, a full review takes approximately 90 seconds on the free tier.

### Events / Trace panel (right)
Shows every ADK event in real time:
- **Model calls** — each `Sending out request` line is one LLM call. You will see 6 per review (one per agent).
- **Tool calls** — expand any event to see which GitHub tools were called and what they returned (PR details, file list, review status).
- **State mutations** — events where an agent writes its output to session state (e.g. `security_assessment`, `architecture_assessment`).
- **Session trace** — click the trace link at the bottom to see the full structured trace for the session, including all tool inputs/outputs and intermediate model responses.

### App tab
Displays the registered ADK app (`cto_orchestrator`) and its agent hierarchy. Use this to confirm the pipeline loaded correctly on startup.

### Sessions tab
Lists all previous sessions. Click any session to replay its trace — useful for debugging a failed governance run without re-running the full pipeline.

---

## Project Structure

```
eng-governance/
├── app/
│   ├── agent.py                  # Root orchestrator, ADK patches, and callbacks
│   ├── agents/
│   │   ├── security_agent.py     # Security risk assessment
│   │   ├── architecture_agent.py # Design and scalability review
│   │   ├── delivery_agent.py     # PR readiness and delivery risk
│   │   ├── cost_agent.py         # Infrastructure cost estimation
│   │   ├── evaluation_agent.py   # CI, review status, and test coverage
│   │   └── _throttle.py          # asyncio.sleep callback between agents
│   ├── schemas/                  # Pydantic output schemas for all agents
│   │   ├── security.py           # SecurityAssessment
│   │   ├── architecture.py       # ArchitectureReview
│   │   ├── delivery.py           # DeliveryPlan
│   │   ├── cost.py               # CostAnalysis
│   │   ├── evaluation.py         # EvaluationReport
│   │   └── governance.py         # GovernanceDecision (final output)
│   ├── tools/
│   │   └── github_tools.py       # GitHub MCP toolset factory with per-agent filtering
│   └── .env                      # Local secrets (not committed)
├── node_modules/
│   └── @modelcontextprotocol/
│       └── server-github/        # Pre-fetched GitHub MCP server (avoids npx at runtime)
├── deployment/
│   └── terraform/
│       └── single-project/       # Terraform config for Cloud Run deployment
├── tests/
│   ├── unit/
│   │   └── test_dummy.py         # Placeholder — add unit tests here
│   ├── integration/
│   │   ├── test_agent.py         # Smoke test: agent produces text output
│   │   └── test_server_e2e.py    # End-to-end HTTP test against the running server
│   └── eval/
│       ├── eval_config.yaml      # Evaluation criteria and thresholds
│       └── datasets/
│           └── governance_eval.json  # 5 labelled test cases
├── Dockerfile                    # Container image for Cloud Run
├── package.json                  # GitHub MCP npm dependency
└── README.md
```

---

## Tests

### Unit tests
```bash
uv run pytest tests/unit
```
Placeholder directory — add fast, isolated tests here for schema validation, keyword detection logic, or callback functions.

### Integration tests
```bash
uv run pytest tests/integration
```
- `test_agent.py` — loads the full agent pipeline in-process and verifies it produces at least one text response for a general chat query. Does not require a running server.
- `test_server_e2e.py` — sends HTTP requests to a locally running `agents-cli playground` instance and verifies end-to-end SSE responses.

Requires `GEMINI_API_KEY` and `GITHUB_PERSONAL_ACCESS_TOKEN` to be set in `app/.env`.

### Eval tests
```bash
agents-cli eval run
```
Runs the agent against 5 labelled governance scenarios defined in `tests/eval/datasets/governance_eval.json`:

| Test case | What it validates |
|---|---|
| `low_risk_pr_approve` | Low-risk doc/comment PR → `APPROVE` |
| `critical_security_reject` | Public S3 bucket → `REJECT` with HITL gate |
| `high_cost_impact_defer` | Large RDS upgrade → `DEFER` or `APPROVE_WITH_CONDITIONS` |
| `blocked_delivery_defer` | Failing CI + changes requested → `DEFER` |
| `architecture_needs_rework` | Cross-service direct DB access → `NEEDS_REWORK` |

Eval criteria (defined in `eval_config.yaml`):
- All 5 specialist agents must be called (threshold: 0.9)
- HITL gate must fire when `requires_human_approval = True` (threshold: 0.85)
- Final output must be a complete `GovernanceDecision` (threshold: 0.9)
- Recommendations must match the risk evidence (threshold: 0.8)
- `CRITICAL` security findings must never produce bare `APPROVE` (threshold: 1.0)

---

## Deployment

### Local container

```bash
docker build -t eng-governance .
docker run -p 8080:8080 --env-file app/.env eng-governance
```

### Cloud Run (via Terraform)

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

Or provision the full infrastructure first:

```bash
agents-cli infra single-project   # Creates Cloud Run service, IAM, storage, telemetry
```

The Terraform configuration in `deployment/terraform/single-project/` sets up:
- Cloud Run service with the container image
- IAM bindings for the service account
- GCS bucket for session storage
- Cloud Trace and BigQuery telemetry exports

---

## Rate Limit Notes

This project makes 6 sequential LLM calls per governance review. On the Gemini API free tier:

| Key type | RPM | TPM | RPD |
|---|---|---|---|
| AI Studio (`AIza...`) | 15 | 1M | 1,500 |
| Vertex AI (`AQ...`) | 5 | 250k | 20 |

**Always use an AI Studio key.** Vertex AI keys have a 20 RPD cap — enough for only 3 full reviews per day.

`INTER_AGENT_DELAY_SECONDS` (default `12`) inserts a pause between agents to spread token usage across the 1-minute TPM window. Set it to `0` when using a paid API key or Vertex AI with billing enabled.

---

## Commands

| Command | Description |
|---|---|
| `agents-cli playground` | Launch local dev UI at `http://localhost:8080` |
| `agents-cli lint` | Run code quality checks |
| `agents-cli eval run` | Run all eval cases against the live agent |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests |
| `agents-cli deploy` | Deploy to Cloud Run |
| `agents-cli infra single-project` | Provision GCP infrastructure via Terraform |
