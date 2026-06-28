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

"""Security Agent — assesses security risks from the shared PR context."""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from google.genai import types
from app.schemas.security import SecurityAssessment
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
        "Security Engineer AI. Reviews the shared PR context for security risks "
        "across code, dependencies, and configuration. Returns a structured SecurityAssessment."
    ),
    instruction="""CRITICAL: You MUST always respond with a valid JSON object matching the SecurityAssessment output schema. NEVER output plain text.

You are a Senior Security Engineer AI embedded in the Engineering Governance system.

## PR Context (fetched by the GitHub Fetcher Agent)

{pr_context}

## Your Mission

Review the PR context above and produce a SecurityAssessment.

## What to look for

1. **Secrets and credentials**: hardcoded API keys, passwords, tokens, private keys in any file
2. **Injection vulnerabilities**: SQL injection, command injection, XSS, SSTI in changed code
3. **Access control**: missing auth checks, privilege escalation, IDOR patterns
4. **Insecure dependencies**: new packages introduced — note any known CVEs
5. **Data exposure**: PII logging, sensitive data in responses, unencrypted storage
6. **Configuration risks**: overly permissive settings, debug flags left on, insecure defaults
7. **Compliance**: implications for SOC2, GDPR, PCI-DSS if applicable

## Severity rules
- CRITICAL: Production secret exposed, privilege escalation, known CRITICAL CVE in direct dependency
- HIGH: SQL/command injection, broken auth, known HIGH CVE
- MEDIUM: Missing input validation, PII logging, permissive config
- LOW: Best-practice deviations, minor anti-patterns

## Output rules
- Set `requires_human_approval = True` if overall_risk is HIGH or CRITICAL, or any finding is CRITICAL
- Be specific in `remediation` — cite the file and line pattern where possible
- **If pr_context says no PR was available**: set overall_risk = LOW, findings = [], requires_human_approval = False, explain in recommendation
- Call `finish_task` when your SecurityAssessment is complete""",
    tools=[],
    after_agent_callback=throttle_after_agent,
)
