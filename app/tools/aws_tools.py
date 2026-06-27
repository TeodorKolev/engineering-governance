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

Package : @yawlabs/aws-mcp  (npm verified — 18 tools)
Requires:
  - Node.js / npx available in the runtime environment (see Dockerfile).
  - AWS credentials via one of:
      a) AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS_REGION (env vars)
      b) Instance profile / Workload Identity Federation (recommended for Cloud Run)
      c) AWS_PROFILE (for local dev with ~/.aws/credentials)

Alternatively, set use_sse=True and point AWS_MCP_SSE_URL at a hosted server.

IMPORTANT — tool architecture:
  This MCP server does NOT expose one tool per AWS API call. Instead it exposes
  generic tools that accept (service, operation, params):

  aws_call(service, operation, params?, query?, region?, profile?)  ← single call
  aws_paginate(service, operation, params?, maxItems?, startingToken?)  ← paginated
  aws_resource_*(typeName, identifier?, desiredState?)  ← Cloud Control API

  For example, the equivalent of our original 'describe_instances' is:
    aws_call(service='ec2', operation='describe-instances')
  And 'get_cost_and_usage' becomes:
    aws_call(service='ce', operation='get-cost-and-usage', params={...})

Live tool list (verified 2026-06-27 via MCP tools/list probe):
  aws_whoami, aws_login_start, aws_login_complete, aws_refresh_if_expiring_soon,
  aws_session_set, aws_session_get, aws_session_clear,
  aws_call, aws_list_profiles, aws_paginate, aws_assume_role, aws_logs_tail,
  aws_resource_get, aws_resource_list, aws_resource_create,
  aws_resource_update, aws_resource_delete, aws_resource_status
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
                args=["-y", "@yawlabs/aws-mcp"],
                env={
                    **os.environ,
                    "AWS_REGION": aws_region,
                },
            )
        )

    return McpToolset(
        connection_params=connection_params,
        # tool_filter uses real tool names from @yawlabs/aws-mcp@1.5.3
        # (verified via MCP tools/list probe on 2026-06-27)
        # Note: aws_call + aws_paginate replace all per-service tools.
        # Governance operations map to:
        #   EC2/VPC: aws_call(service='ec2', operation='describe-instances|describe-security-groups|...')
        #   S3:      aws_call(service='s3api', operation='list-buckets|get-bucket-policy|...')
        #   IAM:     aws_call(service='iam', operation='list-roles|get-policy|...')
        #   Cost:    aws_call(service='ce', operation='get-cost-and-usage|get-cost-forecast')
        #   CW:      aws_logs_tail(logGroupName=...) or aws_call(service='cloudwatch', ...)
        #   RDS:     aws_call(service='rds', operation='describe-db-instances|...')
        #   CCAPI:   aws_resource_get/list for Cloud Control resource reads
        tool_filter=[
            # Identity & session
            "aws_whoami",             # Who am I? Useful for verifying credentials
            "aws_session_get",        # Inspect current session
            # Core data access
            "aws_call",               # Generic AWS CLI call: (service, operation, params)
            "aws_paginate",           # Paginated variant of aws_call
            # Cloud Control API — read resources via CloudFormation schema
            "aws_resource_get",       # Read a single resource (e.g. AWS::S3::Bucket)
            "aws_resource_list",      # List resources of a given type
            # Observability
            "aws_logs_tail",          # Tail CloudWatch Logs for a log group
        ],
    )
