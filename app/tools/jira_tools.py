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

Package : @mcp-devtools/jira  (npm verified — 15 tools)
Requires:
  - Node.js / npx available in the runtime environment (see Dockerfile).
  - JIRA_URL:       Your Jira instance URL (e.g. https://myorg.atlassian.net)
  - JIRA_API_MAIL:  Your Atlassian account email (note: NOT JIRA_USERNAME)
  - JIRA_API_KEY:   Atlassian API token
                    (generate at id.atlassian.com/manage-profile/security/api-tokens)

Alternatively, set use_sse=True and point JIRA_MCP_SSE_URL at a hosted server.

Live tool list (verified 2026-06-27 via MCP tools/list probe):
  execute_jql, get_ticket, read_ticket, get_task, read_task,
  get_only_ticket_name_and_description, create_ticket, edit_ticket,
  delete_ticket, assign_ticket, list_projects, get_all_statuses,
  query_assignable, add_attachment_from_public_url,
  add_attachment_from_confluence
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
        jira_url      = os.environ.get("JIRA_URL", "")
        jira_api_mail = os.environ.get("JIRA_API_MAIL", "")
        jira_api_key  = os.environ.get("JIRA_API_KEY", "")
        # Credential validation is deferred to connection time so that the
        # agent module can be imported without credentials set (e.g. in tests).
        # Note: env var names are JIRA_API_MAIL and JIRA_API_KEY (not USERNAME/TOKEN).
        connection_params = StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@mcp-devtools/jira"],
                env={
                    **os.environ,
                    "JIRA_URL":      jira_url,
                    "JIRA_API_MAIL": jira_api_mail,
                    "JIRA_API_KEY":  jira_api_key,
                },
            )
        )

    return McpToolset(
        connection_params=connection_params,
        # tool_filter uses real tool names from @mcp-devtools/jira@0.2.6
        # (verified via MCP tools/list probe on 2026-06-27)
        tool_filter=[
            # Read operations
            "execute_jql",                           # JQL search — primary discovery tool
            "get_ticket",                            # Full ticket detail by key
            "read_ticket",                           # Alias for get_ticket
            "get_only_ticket_name_and_description",  # Lightweight fetch (summary only)
            "get_task",                              # Task-type issue detail
            "read_task",                             # Alias for get_task
            "list_projects",                         # All accessible Jira projects
            "get_all_statuses",                      # All workflow statuses
            "query_assignable",                      # Users assignable to a project
        ],
    )
