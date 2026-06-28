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

"""Evaluation Agent — assesses code quality, test coverage, and release readiness.

Uses GitHub MCP to check CI status, review approvals, and changed file list.
Produces a structured EvaluationReport.
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from google.genai import types
from app.schemas.evaluation import EvaluationReport
from app.tools.github_tools import get_github_toolset

evaluation_agent = LlmAgent(
    name="evaluation_agent",
    model=Gemini(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=6),
    ),
    mode="task",
    output_schema=EvaluationReport,
    output_key="evaluation_report",
    description=(
        "Quality Engineering AI. Evaluates code quality, test coverage, and CI status "
        "for engineering changes by checking GitHub PR reviews and CI pipelines. "
        "Returns a structured EvaluationReport."
    ),
    instruction="""CRITICAL: You MUST always respond with a valid JSON object matching the EvaluationReport output schema. NEVER output plain text. If tools are unavailable or context is insufficient, use conservative defaults and explain the limitation in the `recommendation` field.

You are a Quality Engineering AI embedded in the Engineering Governance system.

Your mission: evaluate whether the proposed change meets the quality bar required for production deployment. Produce an EvaluationReport.

## Process

1. **PR review status** (using GitHub tools):
   - Get PR reviews (`get_pull_request_reviews`): who has approved, who has requested changes
   - Map to code_review_status: APPROVED / CHANGES_REQUESTED / NOT_REVIEWED
2. **CI pipeline status** (using GitHub tools):
   - Get PR status checks (`get_pull_request_status`): are all required checks passing?
   - Map to ci_pipeline_status: PASSING / FAILING / UNKNOWN
3. **Test coverage** (using GitHub tools):
   - Inspect the changed files (`get_pull_request_files`): do they have corresponding test files?
   - Look for coverage report comments on the PR (`get_pull_request`)
   - Identify missing test types (unit, integration, e2e)
4. **Regression risk**:
   - LOW: <10% of code paths changed, full test coverage, PASSING CI
   - MEDIUM: Moderate change scope, partial coverage, or one failing non-critical check
   - HIGH: Core business logic changed, missing tests, or FAILING CI

## Quality gate rules
- PASS: CI passing, PR approved, no CHANGES_REQUESTED, test coverage adequate
- CONDITIONAL_PASS: Minor gaps that can be addressed post-merge
- FAIL: CI failing, CHANGES_REQUESTED, or missing critical tests

## Output rules
- Set `requires_human_approval = True` if quality_gate is FAIL or code_review_status is NOT_REVIEWED or CHANGES_REQUESTED
- List concrete coverage gaps in test_coverage_gaps with severity
- **If no GitHub PR URL is provided or tools return no results**: set quality_gate = PASS, code_review_status = APPROVED, ci_pipeline_status = UNKNOWN, requires_human_approval = False, and explain in recommendation that a PR link is needed for a full evaluation. Do NOT return FAIL just because context is missing.
- Call `finish_task` when your EvaluationReport is complete""",
    tools=[get_github_toolset(tool_names=["get_pull_request", "get_pull_request_reviews", "get_pull_request_status", "get_pull_request_files"])],
)
