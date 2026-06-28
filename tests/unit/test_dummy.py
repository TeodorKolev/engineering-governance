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

"""Unit tests for schema validation and keyword detection logic."""

import re

import pytest
from pydantic import ValidationError

from app.schemas.cost import CostAnalysis
from app.schemas.governance import GovernanceDecision
from app.schemas.security import SecurityAssessment

# Mirrors the change-request detection in agent.py save_original_input callback.
_CHANGE_KEYWORDS = ["pr", "pull", "github", "commit", "review", "change", "architecture", "deploy"]
_TICKET_PATTERN = re.compile(r'\b[A-Z][A-Z0-9]+-\d+\b')


def _is_change_request(text: str) -> bool:
    return bool(
        any(kw in text.lower() for kw in _CHANGE_KEYWORDS)
        or _TICKET_PATTERN.search(text)
    )


class TestKeywordDetection:
    def test_github_pr_url_detected(self):
        assert _is_change_request("Review https://github.com/acme/api/pull/42")

    def test_ticket_id_detected(self):
        # Jira-style ticket IDs (KAN-1, ENG-42) should trigger the pipeline.
        assert _is_change_request("KAN-1: Add Redis caching to the user-service")

    def test_deploy_keyword_detected(self):
        assert _is_change_request("We want to deploy the payment service today")

    def test_general_chat_skipped(self):
        # Plain questions must not trigger the specialist pipeline.
        assert not _is_change_request("Hello, what does this system do?")

    def test_lowercase_ticket_not_detected(self):
        # Ticket pattern requires uppercase prefix — lowercase should not match.
        assert not _is_change_request("kan-1 some task")


class TestSecurityAssessmentSchema:
    def test_valid_low_risk_assessment(self):
        a = SecurityAssessment(
            overall_risk="LOW",
            findings=[],
            requires_human_approval=False,
            recommendation="No security issues found.",
        )
        assert a.overall_risk == "LOW"
        assert a.requires_human_approval is False

    def test_invalid_risk_level_rejected(self):
        # Schema must reject risk levels outside the defined Literal.
        with pytest.raises(ValidationError):
            SecurityAssessment(
                overall_risk="UNKNOWN",
                findings=[],
                requires_human_approval=False,
                recommendation="x",
            )


class TestGovernanceDecisionSchema:
    def test_valid_approve_decision(self):
        d = GovernanceDecision(
            decision_id="GOV-20260628-test",
            overall_recommendation="APPROVE",
            risk_level="LOW",
            human_approval_required=False,
            timestamp="2026-06-28T00:00:00Z",
        )
        assert d.overall_recommendation == "APPROVE"
        assert d.sub_agent_reports == {}

    def test_invalid_recommendation_rejected(self):
        # MAYBE is not a valid Literal — schema must raise.
        with pytest.raises(ValidationError):
            GovernanceDecision(
                decision_id="GOV-20260628-test",
                overall_recommendation="MAYBE",
                risk_level="LOW",
                human_approval_required=False,
                timestamp="2026-06-28T00:00:00Z",
            )

    def test_conditions_populated_for_conditional_approve(self):
        d = GovernanceDecision(
            decision_id="GOV-20260628-cond",
            overall_recommendation="APPROVE_WITH_CONDITIONS",
            risk_level="HIGH",
            conditions=["Rotate the leaked API key before merging"],
            human_approval_required=True,
            timestamp="2026-06-28T00:00:00Z",
        )
        assert len(d.conditions) == 1
        assert d.human_approval_required is True


class TestCostAnalysisSchema:
    def test_negligible_cost_does_not_require_approval(self):
        c = CostAnalysis(
            cost_impact_level="NEGLIGIBLE",
            resource_impacts=[],
            requires_human_approval=False,
            recommendation="No cost impact.",
        )
        assert c.cost_impact_level == "NEGLIGIBLE"
        assert c.requires_human_approval is False

    def test_invalid_cost_impact_level_rejected(self):
        with pytest.raises(ValidationError):
            CostAnalysis(
                cost_impact_level="EXTREME",
                resource_impacts=[],
                requires_human_approval=True,
                recommendation="x",
            )
