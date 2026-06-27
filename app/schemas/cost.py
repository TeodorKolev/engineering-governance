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

"""Cost analysis schemas for the Cost Agent."""

from typing import Literal

from pydantic import BaseModel, Field


class ResourceCostImpact(BaseModel):
    """Cost impact of a specific AWS resource or service change."""

    resource_type: str = Field(description="AWS resource type (e.g. EC2, RDS, S3, Lambda).")
    resource_id: str | None = Field(
        default=None,
        description="Resource identifier if known.",
    )
    current_monthly_cost_usd: float | None = Field(
        default=None,
        description="Current estimated monthly cost in USD, if measurable.",
    )
    projected_monthly_cost_usd: float | None = Field(
        default=None,
        description="Projected monthly cost after the change in USD.",
    )
    delta_usd: float | None = Field(
        default=None,
        description="Cost delta (positive = increase, negative = saving) in USD per month.",
    )
    notes: str | None = Field(
        default=None,
        description="Explanatory notes about this cost impact.",
    )


class CostAnalysis(BaseModel):
    """Structured cost analysis produced by the Cost Agent."""

    total_monthly_delta_usd: float | None = Field(
        default=None,
        description="Total estimated monthly cost change in USD across all resources.",
    )
    cost_impact_level: Literal["NEGLIGIBLE", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description=(
            "NEGLIGIBLE (<$50/mo), LOW ($50-$500), MEDIUM ($500-$5000), "
            "HIGH ($5000-$50000), CRITICAL (>$50000)."
        )
    )
    resource_impacts: list[ResourceCostImpact] = Field(
        default_factory=list,
        description="Per-resource cost impact breakdown.",
    )
    optimization_opportunities: list[str] = Field(
        default_factory=list,
        description="Cost optimization suggestions identified during analysis.",
    )
    budget_available: bool | None = Field(
        default=None,
        description="Whether the projected cost increase is within the approved budget, if determinable.",
    )
    jira_budget_ticket: str | None = Field(
        default=None,
        description="Jira ticket key for the associated budget approval, if found.",
    )
    requires_human_approval: bool = Field(
        description=(
            "Must be True if cost_impact_level is HIGH or CRITICAL, "
            "or if budget_available is False or unknown."
        )
    )
    recommendation: str = Field(
        description="Plain-language cost recommendation for the CTO Orchestrator."
    )
