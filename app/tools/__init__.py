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

"""MCP tool factory functions for all integrations."""

from app.tools.aws_tools import get_aws_toolset
from app.tools.github_tools import get_github_toolset
from app.tools.jira_tools import get_jira_toolset

__all__ = [
    "get_github_toolset",
    "get_jira_toolset",
    "get_aws_toolset",
]
