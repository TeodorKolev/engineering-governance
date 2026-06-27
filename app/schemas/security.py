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

"""Security assessment schemas for the Security Agent."""

from typing import Literal

from pydantic import BaseModel, Field


class SecurityFinding(BaseModel):
    """A single security finding identified during assessment."""

    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Severity level of the finding."
    )
    title: str = Field(description="Short title of the security finding.")
    description: str = Field(description="Detailed description of the vulnerability or risk.")
    cve_ids: list[str] = Field(
        default_factory=list,
        description="CVE identifiers associated with this finding, if any.",
    )
    affected_components: list[str] = Field(
        default_factory=list,
        description="List of affected services, files, or infrastructure components.",
    )
    remediation: str = Field(description="Recommended remediation steps.")


class SecurityAssessment(BaseModel):
    """Structured security assessment produced by the Security Agent."""

    overall_risk: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Overall risk level of the change under review."
    )
    findings: list[SecurityFinding] = Field(
        default_factory=list,
        description="List of individual security findings, ordered by severity descending.",
    )
    github_pr_url: str | None = Field(
        default=None,
        description="GitHub Pull Request URL that was reviewed, if applicable.",
    )
    infrastructure_scope: list[str] = Field(
        default_factory=list,
        description="AWS resources or infrastructure components in scope.",
    )
    requires_human_approval: bool = Field(
        description=(
            "Must be True if overall_risk is HIGH or CRITICAL, "
            "or if any finding is CRITICAL. The CTO Orchestrator will gate on this."
        )
    )
    recommendation: str = Field(
        description="Plain-language security recommendation for the CTO Orchestrator."
    )
    compliance_notes: str | None = Field(
        default=None,
        description="Notes on compliance implications (SOC2, GDPR, PCI-DSS, etc.).",
    )
