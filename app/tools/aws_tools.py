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

"""AWS MCP toolset factory.

Requires:
  - Node.js / npx available in the runtime environment (see Dockerfile).
  - AWS credentials configured via one of:
      a) AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS_REGION (env vars)
      b) Instance profile / Workload Identity (recommended for Cloud Run via Workload Identity Federation)
      c) AWS_PROFILE (for local dev with ~/.aws/credentials)

The MCP server used is @aws-sdk/client-mcp-server (official AWS MCP package).
Alternatively, set use_sse=True and point AWS_MCP_SSE_URL at a hosted server.
"""

import os

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams, StdioConnectionParams
from mcp import StdioServerParameters


def get_aws_toolset(use_sse: bool = False) -> McpToolset:
    """Return an AWS MCP toolset.

    Args:
        use_sse: If True, connect to a remote AWS MCP server via SSE
                 (set AWS_MCP_SSE_URL). If False (default), launch locally via npx.

    Returns:
        McpToolset configured for AWS resource operations.
    """
    if use_sse:
        sse_url = os.environ.get("AWS_MCP_SSE_URL", "")
        if not sse_url:
            raise ValueError("AWS_MCP_SSE_URL must be set when use_sse=True")
        connection_params = SseConnectionParams(url=sse_url)
    else:
        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        connection_params = StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                args=["-y", "@aws-sdk/client-mcp-server"],
                env={
                    **os.environ,
                    "AWS_REGION": aws_region,
                },
            )
        )

    return McpToolset(
        connection_params=connection_params,
        tool_filter=[
            # EC2 & networking
            "describe_instances",
            "describe_security_groups",
            "describe_vpcs",
            "describe_subnets",
            # S3
            "list_buckets",
            "get_bucket_policy",
            "get_bucket_acl",
            "get_bucket_encryption",
            # IAM
            "list_roles",
            "get_role",
            "list_policies",
            "get_policy",
            # Cost Explorer
            "get_cost_and_usage",
            "get_cost_forecast",
            # CloudWatch
            "describe_alarms",
            "get_metric_statistics",
            # RDS
            "describe_db_instances",
            "describe_db_clusters",
        ],
    )
