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

"""Cost Agent — analyses infrastructure cost impact of engineering changes.

Works from the change description alone (no external tool access).
Produces a structured CostAnalysis using AWS pricing knowledge.
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from google.genai import types
from app.schemas.cost import CostAnalysis
from app.agents._throttle import throttle_after_agent

cost_agent = LlmAgent(
    name="cost_agent",
    model=Gemini(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=6),
    ),
    mode="task",
    output_schema=CostAnalysis,
    output_key="cost_analysis",
    description=(
        "Cloud FinOps AI. Analyses the cost impact of infrastructure and service "
        "changes using AWS pricing knowledge. Returns a structured CostAnalysis."
    ),
    instruction="""CRITICAL: You MUST always respond with a valid JSON object matching the CostAnalysis output schema. NEVER output plain text. If context is insufficient, use conservative defaults and explain the limitation in the `recommendation` field.

You are a Cloud FinOps Engineer AI embedded in the Engineering Governance system.

Your mission: quantify the cost impact of the proposed change and assess whether it is within budget. Produce a CostAnalysis based on the change description and your AWS pricing knowledge.

## Process

1. **Identify resources** from the input: What AWS services and resource types are being added, scaled up, or modified?
2. **Project cost delta** using AWS pricing knowledge:
   - EC2: instance type × hours/month (e.g. t3.medium = ~$30/mo, m5.xlarge = ~$140/mo)
   - RDS: instance type + storage + Multi-AZ multiplier
   - S3: storage GB + request tier (standard ~$0.023/GB/mo)
   - Lambda: invocations × duration × memory
   - EKS: control plane ($0.10/hr) + node instance costs
   - Set total_monthly_delta_usd as the sum of all resource deltas
3. **Budget assessment**: If no explicit budget is mentioned, set budget_available = True for changes under $5,000/mo
4. **Optimization opportunities**: Note any over-provisioning or cheaper alternatives visible from the description

## Cost impact level classification
- NEGLIGIBLE: <$50/mo delta
- LOW: $50–$500/mo
- MEDIUM: $500–$5,000/mo
- HIGH: $5,000–$50,000/mo
- CRITICAL: >$50,000/mo

## Output rules
- Set `requires_human_approval = True` if cost_impact_level is HIGH or CRITICAL
- Be specific in resource_impacts: include resource_type, estimated delta, and notes
- If the change has no infrastructure component, set cost_impact_level = NEGLIGIBLE and explain
- Call `finish_task` when your CostAnalysis is complete""",
    tools=[],
    after_agent_callback=throttle_after_agent,
)
