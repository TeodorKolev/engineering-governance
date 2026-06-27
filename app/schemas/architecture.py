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

"""Architecture review schemas for the Architecture Agent."""

from typing import Literal

from pydantic import BaseModel, Field


class ArchitectureConcern(BaseModel):
    """A single architectural concern or recommendation."""

    category: Literal[
        "scalability",
        "reliability",
        "maintainability",
        "observability",
        "data_model",
        "api_design",
        "dependency",
        "performance",
        "other",
    ] = Field(description="Category of the architectural concern.")
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Severity: LOW (suggestion), MEDIUM (should fix), HIGH (must fix)."
    )
    description: str = Field(description="Description of the concern.")
    recommendation: str = Field(description="Specific actionable recommendation.")


class ArchitectureReview(BaseModel):
    """Structured architecture review produced by the Architecture Agent."""

    overall_assessment: Literal["APPROVED", "APPROVED_WITH_CONCERNS", "NEEDS_REWORK"] = Field(
        description="High-level architectural verdict."
    )
    design_pattern_alignment: str = Field(
        description="Assessment of how well the change aligns with existing architectural patterns."
    )
    concerns: list[ArchitectureConcern] = Field(
        default_factory=list,
        description="List of architectural concerns found, ordered by severity descending.",
    )
    affected_services: list[str] = Field(
        default_factory=list,
        description="List of services or systems impacted by this change.",
    )
    dependency_risks: list[str] = Field(
        default_factory=list,
        description="New dependencies introduced and their associated risks.",
    )
    scalability_assessment: str = Field(
        description="Assessment of how the change performs under increased load."
    )
    requires_human_approval: bool = Field(
        description=(
            "Must be True if overall_assessment is NEEDS_REWORK "
            "or if any concern has HIGH severity."
        )
    )
    recommendation: str = Field(
        description="Plain-language architecture recommendation for the CTO Orchestrator."
    )
