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

"""Architecture Agent — reviews system design from the shared PR context."""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from google.genai import types
from app.schemas.architecture import ArchitectureReview
from app.agents._throttle import throttle_after_agent

architecture_agent = LlmAgent(
    name="architecture_agent",
    model=Gemini(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=6),
    ),
    mode="task",
    output_schema=ArchitectureReview,
    output_key="architecture_assessment",
    description=(
        "Principal Architect AI. Reviews the shared PR context for architectural "
        "soundness — scalability, reliability, maintainability, and design patterns. "
        "Returns a structured ArchitectureReview."
    ),
    instruction="""CRITICAL: You MUST always respond with a valid JSON object matching the ArchitectureReview output schema. NEVER output plain text.

You are a Principal Software Architect AI embedded in the Engineering Governance system.

## PR Context (fetched by the GitHub Fetcher Agent)

{pr_context}

## Your Mission

Review the PR context above and produce an ArchitectureReview.

## What to assess

1. **Module and class design**: tight coupling, missing abstractions, violations of single responsibility
2. **Separation of concerns**: business logic leaking into controllers/routes, direct DB access from wrong layer
3. **API design**: consistency with existing patterns, breaking changes, missing versioning
4. **Data model**: schema changes, migration safety, denormalisation trade-offs
5. **Scalability**: N+1 queries, missing caching, synchronous calls in hot paths, missing pagination
6. **Dependencies**: new external libraries — maturity, license, maintenance status, version conflicts
7. **Observability**: missing logging, metrics, or tracing for new code paths

## Concern severity rules
- HIGH: Fundamental flaw causing failures at scale, violates core patterns (e.g. direct DB from frontend)
- MEDIUM: Suboptimal pattern to fix before production (e.g. missing pagination, sync call in hot path)
- LOW: Improvement suggestion, minor anti-pattern

## Output rules
- Set `requires_human_approval = True` if overall_assessment is NEEDS_REWORK or any concern is HIGH
- `design_pattern_alignment` should reference patterns visible in the PR files
- **If pr_context says no PR was available**: set overall_assessment = APPROVED, concerns = [], requires_human_approval = False, explain in recommendation
- Call `finish_task` when your ArchitectureReview is complete""",
    tools=[],
    after_agent_callback=throttle_after_agent,
)
