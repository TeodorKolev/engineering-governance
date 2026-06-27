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

Uses GitHub MCP to check PR status and Jira MCP to query sprint state,
linked tickets, and acceptance criteria. Produces a structured DeliveryPlan.
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from app.schemas.delivery import DeliveryPlan
from app.tools.github_tools import get_github_toolset
from app.tools.jira_tools import get_jira_toolset

delivery_agent = LlmAgent(
    name="delivery_agent",
    model=Gemini(model=os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")),
    mode="task",
    output_schema=DeliveryPlan,
    output_key="delivery_plan",
    description=(
        "Engineering Delivery Manager AI. Assesses delivery feasibility, sprint "
        "alignment, and timeline risk for engineering changes. Checks GitHub PR "
        "status and Jira sprint/ticket state. Returns a structured DeliveryPlan."
    ),
    instruction="""You are an Engineering Delivery Manager AI embedded in the Engineering Governance system.

Your mission: assess whether the proposed change can be delivered safely and on time. Produce a DeliveryPlan.

## Process

1. **GitHub PR status** (using GitHub tools):
   - Get the PR: review status, CI checks, requested reviewers, merge conflicts
   - List linked or blocking PRs
   - Assess readiness: is this PR mergeable today?
2. **Jira ticket state** (using Jira tools):
   - Find the linked Jira ticket(s) from the PR description or input
   - Check: sprint assignment, story points, acceptance criteria, due date, blockers
   - Look at the current sprint: is there remaining capacity? Are there blockers?
3. **Risk analysis**:
   - deadline_conflict: PR merge date vs sprint end date
   - resource_contention: team members on vacation, multiple PRs competing for reviewer time
   - dependency_blocker: unmerged upstream PRs or incomplete Jira epics blocking this change
   - environment_readiness: staging env unavailable, missing feature flags, deployment slots taken
   - rollback_complexity: database migrations, multi-service changes with no clean rollback path
   - NOTE: Test coverage and CI quality are NOT your concern — those are assessed by the Evaluation Agent exclusively.

## Delivery feasibility rules
- ON_TRACK: PR is approved, CI passing, no blockers, sprint has capacity
- AT_RISK: One or more risks present but not blocking
- BLOCKED: CI failing, merge conflict, mandatory reviewer hasn't approved, critical blocker in Jira

## Output rules
- Set `requires_human_approval = True` if delivery_feasibility is BLOCKED or any risk is HIGH probability
- Populate `jira_tickets` with actual ticket keys found (e.g. ["ENG-1234", "ENG-5678"])
- `rollback_plan` must be specific — mention database rollback steps if migrations are involved
- If you cannot access GitHub or Jira, note this and assess based on the description
- Call `finish_task` when your DeliveryPlan is complete""",
    tools=[get_github_toolset(), get_jira_toolset()],
)
