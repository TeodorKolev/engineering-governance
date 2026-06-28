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

"""Delivery Agent — assesses delivery feasibility and timeline risk.

Uses GitHub MCP to check PR status, review state, and CI checks.
Produces a structured DeliveryPlan.
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from google.genai import types
from app.schemas.delivery import DeliveryPlan
from app.tools.github_tools import get_github_toolset
from app.agents._throttle import throttle_after_agent

delivery_agent = LlmAgent(
    name="delivery_agent",
    model=Gemini(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=6),
    ),
    mode="task",
    output_schema=DeliveryPlan,
    output_key="delivery_plan",
    description=(
        "Engineering Delivery Manager AI. Assesses delivery feasibility and timeline "
        "risk for engineering changes by checking GitHub PR status and CI checks. "
        "Returns a structured DeliveryPlan."
    ),
    instruction="""CRITICAL: You MUST always respond with a valid JSON object matching the DeliveryPlan output schema. NEVER output plain text. If tools are unavailable or context is insufficient, use conservative defaults and explain the limitation in the `recommendation` field.

You are an Engineering Delivery Manager AI embedded in the Engineering Governance system.

Your mission: assess whether the proposed change can be delivered safely and on time. Produce a DeliveryPlan.

## Process

1. **GitHub PR status** (using GitHub tools):
   - Get the PR (`get_pull_request`): review status, CI checks, requested reviewers, merge conflicts, mergeable state
   - Get reviews (`get_pull_request_reviews`): who has approved, who has requested changes
   - Get status checks (`get_pull_request_status`): are all required CI checks passing?
   - Assess readiness: is this PR mergeable today?
2. **Risk analysis**:
   - deadline_conflict: is there a target merge date mentioned and is it realistic?
   - resource_contention: multiple PRs competing for reviewer time
   - dependency_blocker: unmerged upstream PRs blocking this change
   - rollback_complexity: database migrations, multi-service changes with no clean rollback path
   - NOTE: Test coverage and CI quality are NOT your concern — those are assessed by the Evaluation Agent exclusively.

## Delivery feasibility rules
- ON_TRACK: PR is approved, CI passing, no blockers
- AT_RISK: One or more risks present but not blocking
- BLOCKED: CI failing, merge conflict, mandatory reviewer hasn't approved

## Output rules
- Set `requires_human_approval = True` if delivery_feasibility is BLOCKED or any risk is HIGH probability
- `rollback_plan` must be specific — mention database rollback steps if migrations are involved
- **If no GitHub PR URL is provided or GitHub tools return no results**: set delivery_feasibility = ON_TRACK, rollback_plan = "No PR available to assess", requires_human_approval = False, and explain in recommendation that a PR link is needed for a full delivery review. Do NOT return BLOCKED just because context is missing.
- Call `finish_task` when your DeliveryPlan is complete""",
    tools=[get_github_toolset(tool_names=["get_pull_request", "get_pull_request_reviews", "get_pull_request_status"])],
    after_agent_callback=throttle_after_agent,
)
