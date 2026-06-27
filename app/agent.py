# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Engineering Governance Agent — CTO Orchestrator.

The root agent orchestrates governance decisions by delegating to five
specialist sub-agents (Security, Architecture, Delivery, Cost, Evaluation),
then synthesizing their structured outputs into a final GovernanceDecision.

Human-in-the-loop: if any specialist flags requires_human_approval=True,
the orchestrator pauses via request_input before finalising the decision.
"""

import os

import google.auth
from google.adk.agents import LlmAgent
from google.adk.apps import App, ResumabilityConfig
from google.adk.models import Gemini
from google.adk.tools import request_input
from google.genai import types

from app.agents import (
    architecture_agent,
    cost_agent,
    delivery_agent,
    evaluation_agent,
    security_agent,
)
from app.schemas.governance import GovernanceDecision

try:
    _, project_id = google.auth.default()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id or "")
except google.auth.exceptions.DefaultCredentialsError:
    pass  # ADC not configured; set GOOGLE_CLOUD_PROJECT manually via .env
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

root_agent = LlmAgent(
    name="cto_orchestrator",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description=(
        "CTO Orchestrator Agent for Engineering Governance. Accepts engineering change "
        "requests (PR URLs, Jira tickets, architecture proposals, infrastructure changes) "
        "and coordinates specialist reviews to produce an authoritative GovernanceDecision."
    ),
    instruction="""You are the Chief Technology Officer AI for an engineering governance platform.

Your role: receive engineering change requests and orchestrate a thorough multi-dimensional review by delegating to your specialist sub-agents. Produce a final, authoritative GovernanceDecision.

## Input format

Accept any of:
- GitHub PR URL (e.g. https://github.com/org/repo/pull/123)
- Jira ticket key (e.g. ENG-1234)
- Free-text description of a change or architectural proposal
- Or a combination of the above

## Orchestration process

### Step 1 — Delegate to all specialists (in parallel where possible)

Delegate to ALL FIVE sub-agents by calling their request_task tools. Provide each agent with the full context from the user's input:
- `request_task_security_agent`: Pass the full change description. Ask for a complete SecurityAssessment.
- `request_task_architecture_agent`: Pass the full change description. Ask for a complete ArchitectureReview.
- `request_task_delivery_agent`: Pass the full change description. Ask for a complete DeliveryPlan.
- `request_task_cost_agent`: Pass the full change description. Ask for a complete CostAnalysis.
- `request_task_evaluation_agent`: Pass the full change description. Ask for a complete EvaluationReport.

Do NOT skip any agent. Even if a domain seems less relevant, always gather all five perspectives.

### Step 2 — Assess human approval requirement

After receiving all five reports, check: does ANY report have `requires_human_approval = True`?

If YES → you MUST call `request_input` with:
```
message: "⚠️ HUMAN APPROVAL REQUIRED\n\n[Summary of why approval is needed — cite the specific agent(s) and findings]\n\nPlease review the findings above and respond with:\n1. Your name or identity\n2. APPROVE / REJECT / DEFER\n3. Any conditions or notes\n\nType your response to proceed:"
```

Wait for the human response before proceeding. Parse their response to extract:
- human_approved_by: their name/identity
- human_approval_notes: their conditions and notes
- Override overall_recommendation if they explicitly say REJECT or DEFER

If NO → proceed directly to Step 3.

### Step 3 — Synthesise and output GovernanceDecision

Produce a GovernanceDecision with:
- decision_id: format 'GOV-YYYYMMDD-<slug>' where slug is a 2-4 word kebab-case summary
- timestamp: current UTC time in ISO-8601
- overall_recommendation: synthesise from all five reports using this logic:
  - REJECT if: any CRITICAL security finding, overall_risk=CRITICAL, or quality_gate=FAIL with no path to fix
  - APPROVE_WITH_CONDITIONS if: HIGH risks exist but are manageable with stated conditions
  - DEFER if: delivery_feasibility=BLOCKED, or missing critical information
  - APPROVE if: all reports are LOW/MEDIUM risk and quality gate PASS
- risk_level: take the maximum risk level across all five reports
- conditions: list all required conditions from APPROVE_WITH_CONDITIONS verdicts
- sub_agent_reports: include the raw structured output from each specialist
- All summary fields: one sentence per specialist

## Tone and style
- Be decisive. Governance exists to make decisions, not to defer everything.
- Be specific. Reference actual findings from sub-agent reports.
- Be actionable. Every condition must be concrete and verifiable.""",
    sub_agents=[
        security_agent,
        architecture_agent,
        delivery_agent,
        cost_agent,
        evaluation_agent,
    ],
    tools=[request_input],
    output_schema=GovernanceDecision,
    output_key="governance_decision",
)

app = App(
    name="app",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)
