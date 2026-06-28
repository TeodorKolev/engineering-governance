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

"""Evaluation report schemas for the Evaluation Agent."""

from typing import Literal

from pydantic import BaseModel, Field


class TestCoverageGap(BaseModel):
    """A gap in test coverage."""

    gap_type: Literal[
        "missing_unit_tests",
        "missing_integration_tests",
        "missing_e2e_tests",
        "missing_load_tests",
        "missing_regression_tests",
        "insufficient_coverage",
        "other",
    ] = Field(description="Type of test coverage gap.")
    description: str = Field(description="Description of the coverage gap.")
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="How critical this gap is to ship safely."
    )
    affected_components: list[str] = Field(
        default_factory=list,
        description="Components or code paths affected by this gap.",
    )


class QualityMetric(BaseModel):
    """A quality signal or metric from GitHub."""

    metric_name: str = Field(description="Name of the quality metric (e.g. 'test coverage %').")
    current_value: str = Field(description="Current measured value.")
    target_value: str | None = Field(
        default=None,
        description="Target or threshold value.",
    )
    passes_threshold: bool = Field(
        description="Whether the current value meets the target threshold."
    )


class EvaluationReport(BaseModel):
    """Structured evaluation report produced by the Evaluation Agent."""

    quality_gate: Literal["PASS", "CONDITIONAL_PASS", "FAIL"] = Field(
        description=(
            "PASS = ready to ship, CONDITIONAL_PASS = ship with conditions, "
            "FAIL = must fix before shipping."
        )
    )
    test_coverage_gaps: list[TestCoverageGap] = Field(
        default_factory=list,
        description="Identified test coverage gaps.",
    )
    quality_metrics: list[QualityMetric] = Field(
        default_factory=list,
        description="Key quality metrics collected from GitHub.",
    )
    code_review_status: Literal["NOT_REVIEWED", "CHANGES_REQUESTED", "APPROVED"] = Field(
        description="GitHub PR review status."
    )
    ci_pipeline_status: Literal["PASSING", "FAILING", "UNKNOWN"] = Field(
        description="Status of the CI pipeline for the associated PR.",
    )
    open_bugs_count: int = Field(
        default=0,
        description="Number of open bugs linked to this change.",
    )
    regression_risk: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Risk of introducing regressions based on test coverage and scope."
    )
    requires_human_approval: bool = Field(
        description=(
            "Must be True if quality_gate is FAIL "
            "or if code_review_status is NOT_REVIEWED or CHANGES_REQUESTED."
        )
    )
    recommendation: str = Field(
        description="Plain-language evaluation recommendation for the CTO Orchestrator."
    )
