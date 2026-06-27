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

"""GitHub MCP toolset factory.

Requires:
  - Node.js / npx available in the runtime environment (see Dockerfile).
  - GITHUB_TOKEN environment variable set with a Personal Access Token
    that has `repo`, `read:org`, and `read:packages` scopes.

The MCP server used is the official @modelcontextprotocol/server-github package.
In production (Cloud Run), npx downloads and caches the server on first startup.
For air-gapped environments, pre-install with: npx -y @modelcontextprotocol/server-github
"""

import os

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams, StdioConnectionParams
from mcp import StdioServerParameters


def get_github_toolset(use_sse: bool = False) -> McpToolset:
    """Return a GitHub MCP toolset.

    Args:
        use_sse: If True, connect to a remote GitHub MCP server via SSE
                 (set GITHUB_MCP_SSE_URL). If False (default), launch a local
                 stdio-based server via npx — suitable for dev and Cloud Run.

    Returns:
        McpToolset configured for GitHub operations.
    """
    if use_sse:
        sse_url = os.environ.get("GITHUB_MCP_SSE_URL", "")
        if not sse_url:
            raise ValueError(
                "GITHUB_MCP_SSE_URL must be set when use_sse=True"
            )
        connection_params = SseConnectionParams(url=sse_url)
    else:
        github_token = os.environ.get("GITHUB_TOKEN", "")
        # Resolve local node_modules path to optimize startup latency and avoid NPX registry checks
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        local_js = os.path.join(root_dir, "node_modules", "@modelcontextprotocol", "server-github", "dist", "index.js")
        if os.path.exists(local_js):
            command = "node"
            args = [local_js]
        else:
            command = "npx"
            args = ["-y", "@modelcontextprotocol/server-github"]

        connection_params = StdioConnectionParams(
            server_params=StdioServerParameters(
                command=command,
                args=args,
                env={
                    **os.environ,
                    "GITHUB_PERSONAL_ACCESS_TOKEN": github_token,
                },
            )
        )

    return McpToolset(
        connection_params=connection_params,
        # Expose only the tools relevant to governance workflows.
        # Remove tool_filter to expose the full GitHub MCP surface.
        tool_filter=[
            "get_pull_request",
            "list_pull_requests",
            "get_pull_request_files",
            "get_pull_request_reviews",
            "get_pull_request_status",
            "create_issue",
            "get_issue",
            "list_issues",
            "add_issue_comment",
            "get_file_contents",
            "list_commits",
            "get_commit",
            "search_repositories",
            "search_code",
        ],
    )
