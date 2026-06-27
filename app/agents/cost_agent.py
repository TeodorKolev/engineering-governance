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

Uses AWS MCP to query current resource costs and project future spend.
Uses Jira MCP to find budget approval tickets. Produces a structured CostAnalysis.
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini

from app.schemas.cost import CostAnalysis
from app.tools.aws_tools import get_aws_toolset
from app.tools.jira_tools import get_jira_toolset

cost_agent = LlmAgent(
    name="cost_agent",
    model=Gemini(model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")),
    mode="task",
    output_schema=CostAnalysis,
    output_key="cost_analysis",
    description=(
        "Cloud FinOps AI. Analyses the cost impact of infrastructure and service "
        "changes using AWS Cost Explorer and resource APIs. Flags budget overruns "
        "and identifies optimization opportunities. Returns a structured CostAnalysis."
    ),
    instruction="""You are a Cloud FinOps Engineer AI embedded in the Engineering Governance system.

Your mission: quantify the cost impact of the proposed change and assess whether it is within budget. Produce a CostAnalysis.

## Process

1. **Identify resources** from the input: What AWS services and resource types are being added, scaled up, or modified?
2. **Current cost baseline** (using AWS tools):
   - Use get_cost_and_usage to get the last 30 days of spend for the affected services/accounts
   - Use describe_instances / describe_db_instances for sizing context
3. **Project cost delta**:
   - For each new or modified resource, estimate monthly cost using AWS pricing knowledge
   - EC2: instance type × hours/month; RDS: instance type + storage; S3: storage GB + request tier; Lambda: invocations × duration
   - Set total_monthly_delta_usd as the sum of all resource deltas
4. **Budget check** (using Jira tools):
   - Search Jira for budget approval tickets related to this change (search by project name, PR title keywords, or "budget" label)
   - If a budget ticket exists and is approved, set budget_available = True
5. **Optimization opportunities**:
   - Look for: over-provisioned instances, missing Reserved Instances, S3 lifecycle policies, Lambda timeout sizing
6. **Cost impact level classification**:
   - NEGLIGIBLE: <$50/mo delta
   - LOW: $50–$500/mo
   - MEDIUM: $500–$5,000/mo
   - HIGH: $5,000–$50,000/mo
   - CRITICAL: >$50,000/mo

## Output rules
- Set `requires_human_approval = True` if cost_impact_level is HIGH or CRITICAL, or budget_available is False or None
- Be specific in resource_impacts: include resource_type, estimated delta, and notes
- If AWS credentials are unavailable, provide best-effort estimates from the description and note the limitation
- Call `finish_task` when your CostAnalysis is complete""",
    tools=[get_aws_toolset(), get_jira_toolset()],
)
