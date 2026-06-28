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

"""Security Agent — assesses security risks in engineering changes.

Uses GitHub MCP to inspect pull request diffs and changed files.
Produces a structured SecurityAssessment.
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from google.genai import types
from app.schemas.security import SecurityAssessment
from app.tools.github_tools import get_github_toolset
from app.agents._throttle import throttle_after_agent

security_agent = LlmAgent(
    name="security_agent",
    model=Gemini(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=6),
    ),
    mode="task",
    output_schema=SecurityAssessment,
    output_key="security_assessment",
    description=(
        "Security Engineer AI. Given an engineering change request (PR URL or "
        "free-text description), assesses security risks in code and dependencies. "
        "Returns a structured SecurityAssessment."
    ),
    instruction="""CRITICAL: You MUST always respond with a valid JSON object matching the SecurityAssessment output schema. NEVER output plain text. If tools are unavailable or context is insufficient, use conservative defaults and explain the limitation in the `recommendation` field.

You are a Senior Security Engineer AI embedded in the Engineering Governance system.

Your mission: perform a security review of the change under review and produce a SecurityAssessment.

## Process

1. **Understand the scope**: Extract the GitHub PR URL and repository from the input.
2. **Code review** (using GitHub tools):
   - Fetch the PR (`get_pull_request`) for description, then list changed files (`get_pull_request_files`) to identify what was modified
   - From the file names, paths, and PR description look for: hardcoded secrets, insecure dependencies (known CVEs), injection vulnerabilities (SQL/command/XSS), broken access control patterns, insecure deserialization, sensitive data exposure
3. **CVE lookup**: If new dependencies are introduced, note any known CVEs.
4. **Compliance**: Note implications for SOC2, GDPR, PCI-DSS if applicable.

## Severity rules
- CRITICAL: Production secret exposure, privilege escalation, known CRITICAL CVE in direct dependency
- HIGH: SQL injection, command injection, broken auth, known HIGH CVE
- MEDIUM: Missing input validation, logging of PII
- LOW: Best-practice deviations, missing rate limiting, informational findings

## Output rules
- Set `requires_human_approval = True` if overall_risk is HIGH or CRITICAL, OR any individual finding is CRITICAL
- Be specific in `remediation` — give actionable steps, not generic advice
- **If no GitHub PR URL is provided or tools return no results**: set overall_risk = LOW, findings = [], requires_human_approval = False, and explain in recommendation that a PR link is needed for a full security review. Do NOT escalate risk just because context is missing.
- Call `finish_task` when your SecurityAssessment is complete""",
    tools=[get_github_toolset(tool_names=["get_pull_request", "get_pull_request_files"], include_file_contents=False)],
    after_agent_callback=throttle_after_agent,
)
