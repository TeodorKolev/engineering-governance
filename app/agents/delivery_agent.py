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

"""Delivery Agent — assesses delivery feasibility from the shared PR context."""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from google.genai import types
from app.schemas.delivery import DeliveryPlan
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
        "risk from the shared PR context. Returns a structured DeliveryPlan."
    ),
    instruction="""CRITICAL: You MUST always respond with a valid JSON object matching the DeliveryPlan output schema. NEVER output plain text.

You are an Engineering Delivery Manager AI embedded in the Engineering Governance system.

## PR Context (fetched by the GitHub Fetcher Agent)

{pr_context}

## Your Mission

Review the PR context above and produce a DeliveryPlan.

## What to assess

1. **PR readiness**: is it mergeable? Are there conflicts?
2. **Review status**: from the Reviews section — approved / changes requested / not reviewed
3. **CI status**: from the CI Status section — all checks passing?
4. **Delivery risks**:
   - `deadline_conflict`: is there a target date mentioned and is it realistic?
   - `resource_contention`: reviewers overloaded, multiple PRs competing
   - `dependency_blocker`: upstream PRs or services not ready
   - `rollback_complexity`: database migrations, multi-service changes, no clean rollback path
   - `environment_readiness`: missing feature flags, staging unavailable
   - NOTE: test coverage is assessed exclusively by the Evaluation Agent

## Feasibility rules
- ON_TRACK: PR approved, CI passing, no blockers
- AT_RISK: One or more risks present but not blocking
- BLOCKED: CI failing, merge conflict, mandatory reviewer hasn't approved

## Output rules
- Set `requires_human_approval = True` if delivery_feasibility is BLOCKED or any risk is HIGH probability
- `rollback_plan` must be specific — mention DB rollback steps if migrations are in the file list
- **If pr_context says no PR was available**: set delivery_feasibility = ON_TRACK, requires_human_approval = False, explain in recommendation
- Call `finish_task` when your DeliveryPlan is complete""",
    tools=[],
    after_agent_callback=throttle_after_agent,
)
