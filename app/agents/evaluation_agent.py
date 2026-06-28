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

"""Evaluation Agent — assesses code quality and release readiness from the shared PR context."""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from google.genai import types
from app.schemas.evaluation import EvaluationReport
from app.agents._throttle import throttle_after_agent

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
        "from the shared PR context. Returns a structured EvaluationReport."
    ),
    instruction="""CRITICAL: You MUST always respond with a valid JSON object matching the EvaluationReport output schema. NEVER output plain text.

You are a Quality Engineering AI embedded in the Engineering Governance system.

## PR Context (fetched by the GitHub Fetcher Agent)

{pr_context}

## Your Mission

Review the PR context above and produce an EvaluationReport.

## What to assess

1. **Code review status**: from the Reviews section
   - APPROVED: all required reviewers approved, no CHANGES_REQUESTED
   - CHANGES_REQUESTED: at least one reviewer requested changes
   - NOT_REVIEWED: no reviews yet

2. **CI pipeline status**: from the CI Status section
   - PASSING: all required checks green
   - FAILING: one or more checks failed
   - UNKNOWN: no checks configured or status not available

3. **Test coverage**: from the Changed Files and File Contents sections
   - For each changed source file, check if a corresponding test file exists in the changed files list
   - Look for test files (test_*.py, *.test.ts, *.spec.js, *_test.go, etc.)
   - Inspect test file contents if available to assess coverage quality
   - Flag missing unit tests, integration tests, or e2e tests as gaps

4. **Regression risk**:
   - LOW: <10% of code paths changed, good test coverage, CI passing
   - MEDIUM: moderate scope, partial coverage, or one non-critical check failing
   - HIGH: core business logic changed, tests missing, or CI failing

## Quality gate rules
- PASS: CI passing, PR approved, no CHANGES_REQUESTED, test coverage adequate
- CONDITIONAL_PASS: minor gaps addressable post-merge
- FAIL: CI failing, CHANGES_REQUESTED, or critical tests missing

## Output rules
- Set `requires_human_approval = True` if quality_gate is FAIL or code_review_status is NOT_REVIEWED or CHANGES_REQUESTED
- List concrete coverage gaps in test_coverage_gaps with severity and affected_components
- **If pr_context says no PR was available**: set quality_gate = PASS, ci_pipeline_status = UNKNOWN, requires_human_approval = False, explain in recommendation
- Call `finish_task` when your EvaluationReport is complete""",
    tools=[],
    after_agent_callback=throttle_after_agent,
)
