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

"""GitHub Fetcher Agent — collects all PR data once for all specialist agents.

Runs first in the pipeline. Fetches PR metadata, changed files, reviews,
CI status, and file contents, then writes a single pr_context report to
session state. All downstream specialists read from {pr_context} instead
of making their own GitHub tool calls.
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.genai import types

from app.tools.github_tools import get_github_toolset

github_fetcher_agent = LlmAgent(
    name="github_fetcher_agent",
    model=Gemini(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=6),
    ),
    mode="task",
    output_key="pr_context",
    description=(
        "GitHub data collector. Fetches PR metadata, changed files, reviews, "
        "CI status, and file contents from GitHub, then stores a complete snapshot "
        "in session state for all specialist review agents to share."
    ),
    instruction="""You are a GitHub data collector for the Engineering Governance pipeline.

Your ONLY job: fetch all available GitHub PR data and produce a structured report.
You do NOT assess, judge, or recommend anything — that is done by the specialist agents downstream.

⚠️ MANDATORY: You MUST call `get_file_contents` for every relevant source file BEFORE calling
`finish_task`. The specialist agents (security, architecture, evaluation) cannot perform
meaningful reviews without the actual file content. Calling `finish_task` before fetching
file contents is an error and will result in an incomplete governance report.

## Steps — execute ALL of them before calling finish_task

1. **Find the PR reference** in the original request: look for a GitHub URL
   (https://github.com/OWNER/REPO/pull/N) or a pattern like OWNER/REPO#N.

2. **If a PR is found**, call ALL of the following tools:

   a. `get_pull_request(owner, repo, pullNumber)`
      → title, body/description, author, state, labels, mergeable status

   b. `get_pull_request_files(owner, repo, pullNumber)`
      → list every changed file with additions, deletions, and status

   c. `get_pull_request_reviews(owner, repo, pullNumber)`
      → reviewer names and their decision (APPROVED / CHANGES_REQUESTED / COMMENTED)

   d. `get_pull_request_status(owner, repo, pullNumber)`
      → all CI check names and their pass/fail status

   e. ⚠️ REQUIRED — For EACH changed source file (up to 15 files):
      - Call `get_file_contents(owner, repo, path)` — one call per file
      - Skip only: binary files, images, and lock files (package-lock.json, poetry.lock, yarn.lock)
      - Include ALL source code: .py, .ts, .js, .go, .java, .tf, .sql, .yaml, .json, .sh, .md
      - Do NOT skip a file just because you think you have "enough" context
      - You MUST complete all get_file_contents calls before calling finish_task

3. **If no PR is found**, produce a short note explaining that no GitHub PR URL was
   provided, and include whatever context was given in the request.

## Output format

Produce a structured plain-text report exactly as shown below.
This report will be read by five specialist AI agents, so be thorough and accurate.

---
## PR Metadata
- Title: <title>
- Author: <login>
- State: <open|closed|merged>
- Labels: <label1, label2, ...>
- Mergeable: <yes|no|unknown>

### Description
<full PR body text>

---
## Changed Files (<N> total)
- `path/to/file.py` — modified (+42 -7)
- `path/to/new_feature.py` — added (+120 -0)
- `path/to/old.py` — deleted (+0 -55)

---
## Reviews
- <reviewer>: APPROVED
- <reviewer>: CHANGES_REQUESTED — "<their comment>"

---
## CI Status
- <check name>: PASSING
- <check name>: FAILING — "<failure message if available>"

---
## File Contents

### `path/to/file.py`
```
<file content, maximum 150 lines — if longer, include the first 100 and last 50 lines>
```

### `path/to/new_feature.py`
```
<file content>
```
---

Call `finish_task` when your report is complete.""",
    tools=[get_github_toolset(
        include_file_contents=True,
        tool_names=[
            "get_pull_request",
            "get_pull_request_files",
            "get_pull_request_reviews",
            "get_pull_request_status",
        ],
    )],
)
