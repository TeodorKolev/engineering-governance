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
from dotenv import load_dotenv
from typing import Optional

# Load .env from root or app/ directory
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import google.auth
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
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

# Patch to fix task sub-agent event isolation issue in ADK 2.2.0
from google.adk.agents.invocation_context import InvocationContext

_orig_get_events = InvocationContext._get_events

def _patched_get_events(self, *, current_invocation: bool = False, current_branch: bool = False):
    events = _orig_get_events(self, current_invocation=current_invocation, current_branch=current_branch)
    return [e for e in events if getattr(e, "isolation_scope", None) == self.isolation_scope]

InvocationContext._get_events = _patched_get_events

try:
    _, project_id = google.auth.default()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id or "")
except google.auth.exceptions.DefaultCredentialsError:
    pass  # ADC not configured; set GOOGLE_CLOUD_PROJECT manually via .env
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

async def save_original_input(callback_context) -> Optional[types.Content]:
    """Save the initial user request text to the state.
    
    If the request is a general chat message and not a change request, 
    populate default empty assessments in the state and skip parallel execution.
    """
    if callback_context.user_content and callback_context.user_content.parts:
        text = "\n".join(part.text for part in callback_context.user_content.parts if part.text)
        callback_context.state["temp:original_input"] = text
        
        # Check if this looks like a governance/change review request
        is_change_request = any(
            keyword in text.lower()
            for keyword in ["pr", "pull", "github", "jira", "eng-", "aws", "commit", "review", "change", "architecture", "deploy"]
        )
        if not is_change_request:
            from app.schemas.security import SecurityAssessment
            from app.schemas.architecture import ArchitectureReview
            from app.schemas.delivery import DeliveryPlan
            from app.schemas.cost import CostAnalysis
            from app.schemas.evaluation import EvaluationReport

            callback_context.state["security_assessment"] = SecurityAssessment(
                overall_risk="LOW",
                findings=[],
                requires_human_approval=False,
                recommendation="Skipped: General chat query."
            ).model_dump()
            callback_context.state["architecture_assessment"] = ArchitectureReview(
                overall_assessment="APPROVED",
                design_pattern_alignment="Aligned",
                scalability_assessment="No scalability impact",
                concerns=[],
                requires_human_approval=False,
                recommendation="Skipped: General chat query."
            ).model_dump()
            callback_context.state["delivery_plan"] = DeliveryPlan(
                delivery_feasibility="ON_TRACK",
                risks=[],
                requires_human_approval=False,
                rollback_plan="N/A",
                jira_tickets=[],
                recommendation="Skipped: General chat query."
            ).model_dump()
            callback_context.state["cost_analysis"] = CostAnalysis(
                cost_impact_level="NEGLIGIBLE",
                total_monthly_delta_usd=0.0,
                budget_available=True,
                resource_impacts=[],
                requires_human_approval=False,
                recommendation="Skipped: General chat query."
            ).model_dump()
            callback_context.state["evaluation_report"] = EvaluationReport(
                quality_gate="PASS",
                code_review_status="APPROVED",
                ci_pipeline_status="PASSING",
                open_bugs_count=0,
                test_coverage_gaps=[],
                regression_risk="LOW",
                requires_human_approval=False,
                recommendation="Skipped: General chat query."
            ).model_dump()
            # Returning a Content object skips the execution of this agent/node
            return types.Content(role="model", parts=[types.Part.from_text(text="Skipping specialist reviews for general query.")])
    return None

async def post_process_decision(callback_context) -> None:
    """Inject the raw structured reports from the sub-agents into the final synthesized decision."""
    decision = callback_context.state.get("governance_decision")
    if decision:
        security = callback_context.state.get("security_assessment")
        architecture = callback_context.state.get("architecture_assessment")
        delivery = callback_context.state.get("delivery_plan")
        cost = callback_context.state.get("cost_analysis")
        evaluation = callback_context.state.get("evaluation_report")

        def to_dict(val):
            if hasattr(val, "model_dump"):
                return val.model_dump()
            elif hasattr(val, "dict"):
                return val.dict()
            return val

        reports = {}
        if security:
            reports["security_agent"] = to_dict(security)
        if architecture:
            reports["architecture_agent"] = to_dict(architecture)
        if delivery:
            reports["delivery_agent"] = to_dict(delivery)
        if cost:
            reports["cost_agent"] = to_dict(cost)
        if evaluation:
            reports["evaluation_agent"] = to_dict(evaluation)

        if hasattr(decision, "sub_agent_reports"):
            decision.sub_agent_reports = reports
        elif isinstance(decision, dict):
            decision["sub_agent_reports"] = reports

cto_synthesizer = LlmAgent(
    name="cto_synthesizer",
    model=Gemini(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=6),
    ),
    description=(
        "CTO Synthesizer Agent for Engineering Governance. Synthesizes specialist reviews "
        "into a final authoritative GovernanceDecision."
    ),
    instruction="""You are the Chief Technology Officer AI for an engineering governance platform.

Your role: review the assessments provided by your five specialist sub-agents (which have run in parallel) and synthesize them into a final, authoritative GovernanceDecision.

## Specialist Assessments

The reviews from the sub-agents are:
- Security Assessment: {security_assessment}
- Architecture Assessment: {architecture_assessment}
- Delivery Plan: {delivery_plan}
- Cost Analysis: {cost_analysis}
- Evaluation Report: {evaluation_report}

Original change request description: {temp:original_input}

## Step 2 — Assess human approval requirement

After reviewing the five reports, check: does ANY report have `requires_human_approval = True`?

If YES → you MUST call `request_input` with:
```
message: "⚠️ HUMAN APPROVAL REQUIRED\n\n[Summary of why approval is needed — cite the specific agent(s) and findings]\n\nPlease review the findings above and respond with:\n1. Your name or identity\n2. APPROVE / REJECT / DEFER\n3. Any conditions or notes\n\nType your response to proceed:"
```

Wait for the human response before proceeding. Parse their response to extract:
- human_approved_by: their name/identity
- human_approval_notes: their conditions and notes
- Override overall_recommendation if they explicitly say REJECT or DEFER

If NO → proceed directly to Step 3.

## Step 3 — Synthesise and output GovernanceDecision

### 3a. Risk-level normalisation (cross-agent)

Normalise every agent's severity field to the shared 4-level scale before comparing:

| Agent field | Raw value | Normalised risk_level |
|---|---|---|
| SecurityAssessment.overall_risk | CRITICAL | CRITICAL |
| SecurityAssessment.overall_risk | HIGH | HIGH |
| SecurityAssessment.overall_risk | MEDIUM | MEDIUM |
| SecurityAssessment.overall_risk | LOW | LOW |
| ArchitectureReview.overall_assessment | NEEDS_REWORK | HIGH |
| ArchitectureReview.overall_assessment | APPROVED_WITH_CONCERNS | MEDIUM |
| ArchitectureReview.overall_assessment | APPROVED | LOW |
| DeliveryPlan.delivery_feasibility | BLOCKED | HIGH |
| DeliveryPlan.delivery_feasibility | AT_RISK | MEDIUM |
| DeliveryPlan.delivery_feasibility | ON_TRACK | LOW |
| CostAnalysis.cost_impact_level | CRITICAL | CRITICAL |
| CostAnalysis.cost_impact_level | HIGH | HIGH |
| CostAnalysis.cost_impact_level | MEDIUM | MEDIUM |
| CostAnalysis.cost_impact_level | LOW | LOW |
| CostAnalysis.cost_impact_level | NEGLIGIBLE | LOW |
| EvaluationReport.quality_gate | FAIL | HIGH |
| EvaluationReport.quality_gate | CONDITIONAL_PASS | MEDIUM |
| EvaluationReport.quality_gate | PASS | LOW |

Set `risk_level` = maximum of all six normalised values above (CRITICAL > HIGH > MEDIUM > LOW).

### 3b. Recommendation selection rules (strict priority order — stop at first match)

Apply these rules in order. The first rule that matches sets `overall_recommendation`:

1. **REJECT** if ANY of:
   - SecurityAssessment has any SecurityFinding with severity=CRITICAL
   - SecurityAssessment.overall_risk = CRITICAL
   - EvaluationReport.quality_gate = FAIL AND EvaluationReport.code_review_status = NOT_REVIEWED (no path to fix without human)

2. **DEFER** if ANY of:
   - DeliveryPlan.delivery_feasibility = BLOCKED
   - CostAnalysis.budget_available = False or None AND CostAnalysis.cost_impact_level ∈ {HIGH, CRITICAL}
   - Any agent could not access its required tools and the missing data is critical

3. **APPROVE_WITH_CONDITIONS** if ANY of:
   - SecurityAssessment.overall_risk = HIGH (with conditions = remediation steps)
   - ArchitectureReview.overall_assessment = NEEDS_REWORK (with conditions = must-fix concerns)
   - EvaluationReport.quality_gate = FAIL with code_review_status = CHANGES_REQUESTED (fixable path exists)
   - CostAnalysis.cost_impact_level = HIGH and budget_available = True

4. **APPROVE** if:
   - None of the above rules matched
   - All normalised risk levels are LOW or MEDIUM

### 3c. Conflict resolution between agents

When two agents produce contradictory signals, apply these tie-breaker rules:

| Conflict scenario | Resolution |
|---|---|
| Security=APPROVE but Evaluation=FAIL | FAIL takes precedence → REJECT or APPROVE_WITH_CONDITIONS |
| Architecture=NEEDS_REWORK but Delivery=ON_TRACK | NEEDS_REWORK takes precedence → APPROVE_WITH_CONDITIONS |
| Cost=CRITICAL but all others=LOW | Cost CRITICAL triggers REJECT (budget uncontrolled) |
| Delivery=BLOCKED but Security+Arch both APPROVE | BLOCKED triggers DEFER (can't ship safely anyway) |
| Human says APPROVE but Security=CRITICAL | Security CRITICAL is non-overridable → REJECT (note override attempt in human_approval_notes) |

### 3d. GovernanceDecision output

Produce the final GovernanceDecision:
- `decision_id`: format `GOV-YYYYMMDD-<slug>` (slug = 2-4 word kebab-case of the change)
- `timestamp`: current UTC time in ISO-8601
- `overall_recommendation`: result of Step 3b
- `risk_level`: result of Step 3a
- `conditions`: concrete, verifiable conditions (only for APPROVE_WITH_CONDITIONS)
- `sub_agent_reports`: raw structured output from each specialist (will be automatically post-processed and filled)
- `security_summary` / `architecture_summary` / `delivery_summary` / `cost_summary` / `evaluation_summary`: one sentence each, citing specific findings
- `human_approval_required`: True if any agent's requires_human_approval was True
- `human_approved_by` / `human_approval_notes`: populated from Step 2 response if HITL fired

## Tone and style
- Be decisive. Governance exists to make decisions, not to defer everything.
- Be specific. Reference actual agent findings by name and severity.
- Be actionable. Every condition must be concrete and verifiable (not "fix security issues").""",
    tools=[request_input],
    output_schema=GovernanceDecision,
    output_key="governance_decision",
    after_agent_callback=post_process_decision,
)

specialist_reviewers = ParallelAgent(
    name="specialist_reviewers",
    sub_agents=[
        security_agent,
        architecture_agent,
        delivery_agent,
        cost_agent,
        evaluation_agent,
    ],
    before_agent_callback=save_original_input,
)

root_agent = SequentialAgent(
    name="cto_orchestrator",
    sub_agents=[
        specialist_reviewers,
        cto_synthesizer,
    ],
)

app = App(
    name="app",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)
