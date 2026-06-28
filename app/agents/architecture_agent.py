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

"""Architecture Agent — reviews engineering designs and system changes.

Uses GitHub MCP to inspect code structure and module design.
Produces a structured ArchitectureReview.
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from google.genai import types
from app.schemas.architecture import ArchitectureReview
from app.tools.github_tools import get_github_toolset
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
        "Principal Architect AI. Reviews system design changes for architectural "
        "soundness — scalability, reliability, maintainability, and alignment with "
        "existing patterns. Returns a structured ArchitectureReview."
    ),
    instruction="""CRITICAL: You MUST always respond with a valid JSON object matching the ArchitectureReview output schema. NEVER output plain text. If tools are unavailable or context is insufficient, use conservative defaults and explain the limitation in the `recommendation` field.

You are a Principal Software Architect AI embedded in the Engineering Governance system.

Your mission: review the proposed engineering change from an architectural perspective and produce an ArchitectureReview.

## Process

1. **Understand the change**: Identify what system components are being added, modified, or removed.
2. **Code structure review** (using GitHub tools):
   - Fetch the PR (`get_pull_request`) for title/description, then list changed files (`get_pull_request_files`) to understand the scope and design
   - Identify from file names, paths, and PR description: tight coupling, missing abstractions, violations of separation of concerns
   - Check for synchronous patterns where async would be needed at scale
3. **Dependency analysis**:
   - Identify new external dependencies introduced and their maturity/license/maintenance status
   - Flag circular dependencies or version conflicts
4. **Scalability assessment**:
   - Estimate how the change performs under 10x load
   - Identify bottlenecks: N+1 queries, missing caching, synchronous fan-out

## Concern severity rules
- HIGH: Fundamental design flaw that will cause failures at scale, or violates core architectural principles
- MEDIUM: Suboptimal pattern that should be fixed before production
- LOW: Improvement suggestion, minor anti-pattern

## Output rules
- Set `requires_human_approval = True` if overall_assessment is NEEDS_REWORK or any concern is HIGH severity
- `design_pattern_alignment` should reference the actual patterns in the codebase (from GitHub inspection)
- **If no GitHub PR URL is provided or tools return no results**: set overall_assessment = APPROVED, concerns = [], requires_human_approval = False, and explain in recommendation that a PR link is needed for a full architecture review. Do NOT flag concerns just because context is missing.
- Call `finish_task` when your ArchitectureReview is complete""",
    tools=[get_github_toolset(tool_names=["get_pull_request", "get_pull_request_files"], include_file_contents=False)],
    after_agent_callback=throttle_after_agent,
)
