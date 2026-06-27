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


from typing import Any, List, Optional
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams, StdioConnectionParams
from mcp import StdioServerParameters


# Global in-memory cache for file contents
_file_contents_cache = {}


class CachedGetFileContents(BaseTool):
    def __init__(self, raw_mcp_toolset: McpToolset):
        super().__init__(
            name="get_file_contents",
            description="Get the contents of a file or directory in a repository (Cached version)"
        )
        self.raw_mcp_toolset = raw_mcp_toolset

    def _get_declaration(self) -> types.FunctionDeclaration:
        from google.adk.features import FeatureName, is_feature_enabled
        
        schema = {
            'type': 'object',
            'properties': {
                'owner': {'type': 'string', 'description': 'The owner of the repository'},
                'repo': {'type': 'string', 'description': 'The name of the repository'},
                'path': {'type': 'string', 'description': 'The path to the file or directory'},
                'branch': {'type': 'string', 'description': 'The branch or commit ref (optional)'}
            },
            'required': ['owner', 'repo', 'path']
        }
        
        if is_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL):
            return types.FunctionDeclaration(
                name=self.name,
                description=self.description,
                parameters_json_schema=schema
            )
        else:
            return types.FunctionDeclaration(
                name=self.name,
                description=self.description,
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        'owner': types.Schema(type=types.Type.STRING, description='The owner of the repository'),
                        'repo': types.Schema(type=types.Type.STRING, description='The name of the repository'),
                        'path': types.Schema(type=types.Type.STRING, description='The path to the file or directory'),
                        'branch': types.Schema(type=types.Type.STRING, description='The branch or commit ref (optional)'),
                    },
                    required=['owner', 'repo', 'path']
                )
            )

    async def run_async(self, *, args: dict, tool_context: ToolContext) -> Any:
        owner = args.get("owner")
        repo = args.get("repo")
        path = args.get("path")
        branch = args.get("branch")
        
        cache_key = (owner, repo, path, branch)
        if cache_key in _file_contents_cache:
            return _file_contents_cache[cache_key]
            
        # Get the underlying raw tool
        tools = await self.raw_mcp_toolset.get_tools(tool_context._invocation_context)
        raw_tool = next((t for t in tools if t.name == "get_file_contents"), None)
        if not raw_tool:
            raise ValueError("Underlying get_file_contents tool not found in MCP toolset.")
            
        result = await raw_tool.run_async(args=args, tool_context=tool_context)
        _file_contents_cache[cache_key] = result
        return result


class CachedGithubToolset(McpToolset):
    def __init__(self, raw_github_toolset: McpToolset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.raw_github_toolset = raw_github_toolset

    async def get_tools(self, readonly_context = None) -> List[BaseTool]:
        tools = await super().get_tools(readonly_context)
        cached_tool = CachedGetFileContents(self.raw_github_toolset)
        tools.append(cached_tool)
        return tools

    async def close(self) -> None:
        await super().close()
        await self.raw_github_toolset.close()


def get_github_toolset(use_sse: bool = False, include_raw_get_file_contents: bool = False) -> McpToolset:
    """Return a GitHub MCP toolset.

    Args:
        use_sse: If True, connect to a remote GitHub MCP server via SSE
                 (set GITHUB_MCP_SSE_URL). If False (default), launch a local
                 stdio-based server via npx — suitable for dev and Cloud Run.
        include_raw_get_file_contents: If True, include raw get_file_contents in the filter.

    Returns:
        McpToolset configured for GitHub operations.
    """
    sse_url = os.environ.get("GITHUB_MCP_SSE_URL", "")
    if use_sse or sse_url:
        if not sse_url:
            raise ValueError(
                "GITHUB_MCP_SSE_URL must be set when use_sse=True"
            )
        connection_params = SseConnectionParams(url=sse_url)
    else:
        github_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
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

    # Expose only the tools relevant to governance workflows.
    tool_filter = [
        "get_pull_request",
        "list_pull_requests",
        "get_pull_request_files",
        "get_pull_request_reviews",
        "get_pull_request_status",
        "create_issue",
        "get_issue",
        "list_issues",
        "add_issue_comment",
        "list_commits",
        "get_commit",
        "search_repositories",
        "search_code",
    ]
    
    if include_raw_get_file_contents:
        tool_filter.append("get_file_contents")
        return McpToolset(
            connection_params=connection_params,
            tool_filter=tool_filter,
        )

    raw_github_toolset = get_github_toolset(
        use_sse=use_sse,
        include_raw_get_file_contents=True
    )

    return CachedGithubToolset(
        raw_github_toolset=raw_github_toolset,
        connection_params=connection_params,
        tool_filter=tool_filter,
    )
