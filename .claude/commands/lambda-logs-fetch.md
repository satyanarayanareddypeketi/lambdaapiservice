# Skill: Lambda Logs Fetch

## Purpose
Fetch and analyse CloudWatch logs for a given AWS Lambda function.
Supports filtering by time range, log level, error keywords, and correlation/trace ID.

## Trigger
Invoked when a developer needs to debug a Lambda function or investigate a failed invocation.

## Inputs

| Parameter | Required | Description |
|---|---|---|
| `function_name` | YES | Name or ARN of the Lambda function |
| `environment` | YES | Target environment: dev / staging / prod |
| `start_time` | NO | Start of log window (ISO 8601 or relative: `15m`, `1h`, `24h`). Default: last 15 minutes |
| `end_time` | NO | End of log window. Default: now |
| `filter_pattern` | NO | CloudWatch filter pattern (e.g. `ERROR`, `"timeout"`, `{ $.level = "ERROR" }`) |
| `trace_id` | NO | Correlation or X-Ray trace ID to isolate a single invocation |
| `limit` | NO | Max number of log events to return. Default: 100. Max: 500 |

## Authentication

Authentication uses your local AWS credentials — no separate login is needed if your CLI is already configured.

The skill resolves credentials in this order (standard AWS credential chain):
1. Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
2. Named profile: pass `--profile {profile_name}` to target a specific profile from `~/.aws/credentials` or `~/.aws/config`
3. AWS SSO: run `aws sso login --profile {profile_name}` before invoking if using IAM Identity Center
4. Instance/container role: used automatically if running inside EC2 or ECS

**Required IAM permissions for the caller:**
```
logs:FilterLogEvents
logs:GetLogEvents
logs:DescribeLogStreams
logs:DescribeLogGroups
```

> If targeting `prod`, ensure your local profile has MFA or SSO session active before invoking.

## Steps

1. **Resolve log group**
   - Log group name: `/aws/lambda/{function_name}`
   - If function ARN is provided, extract function name from the ARN

2. **Validate environment access**
   - Check caller has read access to the target environment log group
   - If environment is `prod`, emit an audit log entry before fetching

3. **Fetch logs**
   - Use `aws logs filter-log-events` with the resolved log group, time range, and filter pattern
   - If `trace_id` is provided, append it to the filter pattern: `"{trace_id}"`
   - Paginate until `limit` is reached or results are exhausted

4. **Parse and structure results**
   - Detect log format: structured JSON vs unstructured string
   - For JSON logs: extract `timestamp`, `level`, `message`, `traceId`, `requestId`
   - For unstructured logs: extract timestamp and raw message
   - Flag any log lines containing: `ERROR`, `WARN`, `Exception`, `Traceback`, `Task timed out`

5. **Summarise findings**
   - Total events fetched
   - Count by log level (ERROR / WARN / INFO)
   - First error message found (if any)
   - Unique request IDs seen
   - Any cold start indicators (`Init Duration` in REPORT lines)

## Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKILL: Lambda Logs Fetch
FUNCTION: {function_name}
ENVIRONMENT: {environment}
WINDOW: {start_time} → {end_time}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY:
  Total events : {n}
  ERROR        : {n}
  WARN         : {n}
  INFO         : {n}
  Cold starts  : {n}

ERRORS FOUND:
  [{timestamp}] [{requestId}] {message}
  ...

RAW LOGS (most recent first, up to limit):
  [{timestamp}] {message}
  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## AWS CLI Commands Reference

```bash
# Fetch logs with a filter pattern
aws logs filter-log-events \
  --log-group-name "/aws/lambda/{function_name}" \
  --start-time {epoch_ms} \
  --end-time {epoch_ms} \
  --filter-pattern "{filter_pattern}" \
  --limit {limit} \
  --region {region}

# Fetch the latest log stream only
aws logs describe-log-streams \
  --log-group-name "/aws/lambda/{function_name}" \
  --order-by LastEventTime \
  --descending \
  --limit 1

# Get log events from a specific stream
aws logs get-log-events \
  --log-group-name "/aws/lambda/{function_name}" \
  --log-stream-name "{stream_name}" \
  --start-from-head
```

## Governance Checks Applied
- Audit log written before any prod log access (CMP-001)
- PII must not be displayed in output — mask email, SSN, card patterns (CMP-002, PY-P-005)
- Read-only operation — no log deletion or modification permitted

## Error Handling

| Error | Response |
|---|---|
| Log group not found | Return clear message: function may not have been invoked or name is wrong |
| Access denied | Return message with required IAM permissions: `logs:FilterLogEvents`, `logs:GetLogEvents` |
| No events in window | Return summary with zero counts and suggest widening the time range |
| Rate limited | Retry with exponential backoff (max 3 retries) |
