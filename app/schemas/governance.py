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

"""Top-level governance decision schema — the final output of the CTO Orchestrator."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class GovernanceDecision(BaseModel):
    """
    Final governance decision produced by the CTO Orchestrator Agent.

    Aggregates findings from all specialist sub-agents into a single
    authoritative engineering governance record.
    """

    decision_id: str = Field(
        description=(
            "Unique decision identifier. Use format 'GOV-<YYYYMMDD>-<SHORT_SLUG>', "
            "e.g. 'GOV-20260627-s3-public-access'."
        )
    )
    request_summary: str = Field(
        description="One-paragraph summary of what was reviewed and why."
    )
    overall_recommendation: Literal[
        "APPROVE",
        "APPROVE_WITH_CONDITIONS",
        "DEFER",
        "REJECT",
    ] = Field(
        description=(
            "APPROVE: safe to proceed. "
            "APPROVE_WITH_CONDITIONS: proceed after addressing listed conditions. "
            "DEFER: needs more information or investigation. "
            "REJECT: must not proceed."
        )
    )
    conditions: list[str] = Field(
        default_factory=list,
        description=(
            "Required conditions that must be met before proceeding. "
            "Populated when overall_recommendation is APPROVE_WITH_CONDITIONS."
        ),
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Aggregate risk level synthesized from all specialist reports."
    )
    security_summary: str = Field(
        description="One-sentence summary of the security assessment."
    )
    architecture_summary: str = Field(
        description="One-sentence summary of the architecture review."
    )
    delivery_summary: str = Field(
        description="One-sentence summary of the delivery plan assessment."
    )
    cost_summary: str = Field(
        description="One-sentence summary of the cost analysis."
    )
    evaluation_summary: str = Field(
        description="One-sentence summary of the evaluation report."
    )
    sub_agent_reports: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Raw structured outputs from each specialist agent, keyed by agent name: "
            "'security_agent', 'architecture_agent', 'delivery_agent', "
            "'cost_agent', 'evaluation_agent'."
        ),
    )
    human_approval_required: bool = Field(
        description=(
            "True if any specialist agent flagged requires_human_approval=True. "
            "The orchestrator must call request_input before finalizing."
        )
    )
    human_approved_by: str | None = Field(
        default=None,
        description=(
            "Identity of the human approver (e.g. their name or email). "
            "Populated after HITL approval; None if no approval was required."
        ),
    )
    human_approval_notes: str | None = Field(
        default=None,
        description="Notes provided by the human approver during HITL review.",
    )
    timestamp: str = Field(
        description="ISO-8601 UTC timestamp when this decision was produced."
    )
