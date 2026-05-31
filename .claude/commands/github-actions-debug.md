# Skill: GitHub Actions Run Logs Debugger

## Purpose
Fetch and analyse logs from a GitHub Actions workflow run to debug failures,
identify failing steps, and surface actionable error messages.
Read-only — no workflow triggers, reruns, or modifications.

## Trigger
Invoked when a developer needs to debug a failed or stuck GitHub Actions workflow run.

## Authentication

Authentication uses your local GitHub credentials — no separate login needed if
the GitHub CLI (`gh`) is already configured.

The skill uses the `gh` CLI which resolves credentials in this order:
1. `GH_TOKEN` environment variable
2. `GITHUB_TOKEN` environment variable
3. Local `gh` auth: run `gh auth login` once to store credentials in `~/.config/gh/`
4. Named host token in `~/.config/gh/hosts.yml`

**Verify auth before invoking:**
```bash
gh auth status
```

**Required GitHub token scopes:**
```
repo          (for private repositories)
actions:read  (to read workflow runs and logs)
```

> For org repositories with SSO enforced, run `gh auth refresh` to ensure
> your token is SSO-authorized for the target organisation.

---

## Inputs

| Parameter | Required | Description |
|---|---|---|
| `repo` | YES | Repository in `{owner}/{repo}` format (e.g. `myorg/my-service`) |
| `run_id` | NO | Specific workflow run ID to inspect. If omitted, fetches the latest failed run |
| `workflow` | NO | Workflow file name or ID to filter by (e.g. `deploy.yml`). Used when `run_id` is omitted |
| `branch` | NO | Branch to filter runs by. Default: repo default branch |
| `job_name` | NO | Narrow output to a specific job name within the run |
| `limit` | NO | Max number of log lines to return per failing step. Default: 50. Max: 200 |

---

## Steps

1. **Resolve the target run**
   - If `run_id` is provided: fetch that run directly
   - If omitted: list recent runs filtered by `workflow` and `branch`, pick the latest
     run with status `failure` or `cancelled`
   - If no failed run is found: report the latest run regardless of status

2. **Fetch run summary**
   - Get run metadata: workflow name, trigger event, branch, commit SHA, actor,
     created/updated timestamps, conclusion

3. **List jobs in the run**
   - Fetch all jobs for the run
   - Identify jobs with conclusion `failure`, `cancelled`, or `timed_out`
   - If `job_name` is provided, filter to that job only

4. **Fetch logs for failing jobs**
   - For each failing job, download the log using `gh run view --log`
   - Identify the failing step (first step with conclusion `failure`)
   - Extract up to `limit` lines around the failure point:
     - 5 lines before the error
     - All lines from the error to end of step or `limit`, whichever comes first
   - Flag lines containing: `Error`, `error:`, `FAILED`, `exit code`, `Process completed with exit code [^0]`,
     `fatal:`, `npm ERR!`, `ModuleNotFoundError`, `SyntaxError`, `timed out`

5. **Summarise findings**
   - Overall run conclusion
   - Total jobs: passed / failed / skipped
   - Name of first failing job and step
   - Root cause snippet (the flagged error lines)
   - Suggested next action based on error type (see Error Pattern table below)

---

## Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKILL: GitHub Actions Run Debugger
REPO: {owner}/{repo}
RUN ID: {run_id}
WORKFLOW: {workflow_name}
BRANCH: {branch}
TRIGGERED BY: {actor} via {event}
CONCLUSION: {conclusion}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

JOBS SUMMARY:
  ✓ passed  : {n}
  ✗ failed  : {n}
  ⊘ skipped : {n}

FIRST FAILING JOB: {job_name}
FIRST FAILING STEP: {step_name}

ROOT CAUSE:
  {flagged error lines}

FULL STEP LOG (last {limit} lines):
  {log lines}

SUGGESTED ACTION:
  {one-line recommendation based on error pattern}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## gh CLI Commands Reference

```bash
# Check auth status
gh auth status

# List recent workflow runs for a repo
gh run list --repo {owner}/{repo} --workflow {workflow.yml} --branch {branch} --limit 10

# View run summary
gh run view {run_id} --repo {owner}/{repo}

# View logs for a specific run (all jobs)
gh run view {run_id} --repo {owner}/{repo} --log

# View logs for a specific job only
gh run view {run_id} --repo {owner}/{repo} --log --job {job_id}

# View logs for failing steps only
gh run view {run_id} --repo {owner}/{repo} --log-failed

# List jobs in a run
gh api repos/{owner}/{repo}/actions/runs/{run_id}/jobs --jq '.jobs[] | {id, name, conclusion, steps: [.steps[] | select(.conclusion=="failure")]}'
```

---

## Common Error Patterns and Suggested Actions

| Error Pattern | Likely Cause | Suggested Action |
|---|---|---|
| `exit code 1` on test step | Test failures | Run tests locally; check test output above the exit line |
| `secret not found` / `Context access might be invalid` | Missing or misspelled GitHub secret | Check repo/org secrets in Settings → Secrets and variables |
| `npm ERR! / pip error / ModuleNotFoundError` | Dependency install failure | Check pinned versions; clear cache by re-running with cache disabled |
| `Process completed with exit code 128` on git step | Git auth failure or missing ref | Check `actions/checkout` step and token permissions |
| `timed out` | Job exceeded `timeout-minutes` | Increase timeout or investigate slow step (GA-005) |
| `Resource not accessible by integration` | Token missing required scope | Add required permissions block to workflow (GA-008) |
| `self-hosted runner: offline` | Runner unavailable | Check runner registration in Settings → Actions → Runners |

---

## Governance Checks Applied
- Read-only — no `gh run rerun`, `gh run cancel`, or workflow dispatch commands permitted
- Logs must not be stored or forwarded outside the local session
- Sensitive values visible in logs (tokens, passwords) must be flagged and reported to the repo owner, not displayed in output (GA-004, SP-001)
