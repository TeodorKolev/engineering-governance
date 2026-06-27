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

"""Delivery plan schemas for the Delivery Agent."""

from typing import Literal

from pydantic import BaseModel, Field


class DeliveryRisk(BaseModel):
    """A delivery or timeline risk."""

    risk_type: Literal[
        "deadline_conflict",
        "resource_contention",
        "dependency_blocker",
        "scope_creep",
        "testing_gap",
        "rollback_complexity",
        "other",
    ] = Field(description="Type of delivery risk.")
    description: str = Field(description="Description of the risk.")
    probability: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Probability that this risk materializes."
    )
    mitigation: str = Field(description="Suggested mitigation strategy.")


class DeliveryPlan(BaseModel):
    """Structured delivery plan produced by the Delivery Agent."""

    delivery_feasibility: Literal["ON_TRACK", "AT_RISK", "BLOCKED"] = Field(
        description="Current delivery status assessment."
    )
    estimated_merge_date: str | None = Field(
        default=None,
        description="Estimated merge/release date in ISO-8601 format (YYYY-MM-DD).",
    )
    jira_tickets: list[str] = Field(
        default_factory=list,
        description="Linked Jira ticket keys (e.g. ENG-1234) relevant to this change.",
    )
    open_pull_requests: list[str] = Field(
        default_factory=list,
        description="GitHub PR URLs that are open and blocking or related.",
    )
    risks: list[DeliveryRisk] = Field(
        default_factory=list,
        description="Delivery risks identified, ordered by probability descending.",
    )
    missing_acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Acceptance criteria or definition-of-done items that are missing.",
    )
    rollback_plan: str = Field(
        description="Rollback strategy if this change needs to be reverted."
    )
    requires_human_approval: bool = Field(
        description=(
            "Must be True if delivery_feasibility is BLOCKED "
            "or if any risk has HIGH probability."
        )
    )
    recommendation: str = Field(
        description="Plain-language delivery recommendation for the CTO Orchestrator."
    )
