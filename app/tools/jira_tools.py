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

"""Jira MCP toolset factory.

Requires:
  - Node.js / npx available in the runtime environment (see Dockerfile).
  - JIRA_URL:        Your Jira instance URL (e.g. https://myorg.atlassian.net)
  - JIRA_USERNAME:   Your Atlassian account email
  - JIRA_API_TOKEN:  Atlassian API token (generate at id.atlassian.com/manage-profile/security/api-tokens)

The MCP server used is @modelcontextprotocol/server-jira (community package).
Alternatively, set use_sse=True and point JIRA_MCP_SSE_URL at a hosted server.
"""

import os

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams, StdioConnectionParams
from mcp import StdioServerParameters


def get_jira_toolset(use_sse: bool = False) -> McpToolset:
    """Return a Jira MCP toolset.

    Args:
        use_sse: If True, connect to a remote Jira MCP server via SSE
                 (set JIRA_MCP_SSE_URL). If False (default), launch locally via npx.

    Returns:
        McpToolset configured for Jira operations.
    """
    if use_sse:
        sse_url = os.environ.get("JIRA_MCP_SSE_URL", "")
        if not sse_url:
            raise ValueError("JIRA_MCP_SSE_URL must be set when use_sse=True")
        connection_params = SseConnectionParams(url=sse_url)
    else:
        jira_url = os.environ.get("JIRA_URL", "")
        jira_username = os.environ.get("JIRA_USERNAME", "")
        jira_api_token = os.environ.get("JIRA_API_TOKEN", "")
        # Credential validation is deferred to connection time so that the
        # agent module can be imported without credentials set (e.g. in tests).
        connection_params = StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-jira"],
                env={
                    **os.environ,
                    "JIRA_URL": jira_url,
                    "JIRA_USERNAME": jira_username,
                    "JIRA_API_TOKEN": jira_api_token,
                },
            )
        )

    return McpToolset(
        connection_params=connection_params,
        tool_filter=[
            "get_issue",
            "search_issues",
            "list_issues",
            "create_issue",
            "update_issue",
            "add_comment",
            "get_project",
            "list_projects",
            "get_sprint",
            "list_sprints",
            "get_board",
        ],
    )
