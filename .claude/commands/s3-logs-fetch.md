# Skill: S3 Logs Fetch

## Purpose
Fetch and analyse logs stored in an S3 bucket.
Supports two log types: S3 Server Access Logs and application logs written directly to S3.
Filters by time range, prefix, HTTP status, error codes, and source IP.

## Trigger
Invoked when a developer needs to investigate S3 access patterns, debug 4xx/5xx errors,
audit who accessed an object, or analyse application logs stored in S3.

## Inputs

| Parameter | Required | Description |
|---|---|---|
| `bucket_name` | YES | Name of the S3 bucket to fetch logs from |
| `log_type` | YES | `server-access` (S3 access logs) or `application` (app logs written to S3) |
| `environment` | YES | Target environment: dev / staging / prod |
| `prefix` | NO | S3 key prefix to scope the search (e.g. `logs/2024/05/`, `AWSLogs/`) |
| `start_time` | NO | Start of log window (ISO 8601 or relative: `1h`, `24h`, `7d`). Default: last 1 hour |
| `end_time` | NO | End of log window. Default: now |
| `filter_status` | NO | HTTP status code filter for server-access logs (e.g. `4`, `5` for 4xx/5xx, or exact `403`) |
| `filter_key` | NO | Filter log entries by a specific S3 object key |
| `filter_ip` | NO | Filter by requester IP address |
| `limit` | NO | Max number of log entries to return. Default: 200. Max: 1000 |

## Authentication

Authentication uses your local AWS credentials — no separate login is needed if your CLI is already configured.

The skill resolves credentials in this order (standard AWS credential chain):
1. Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
2. Named profile: pass `--profile {profile_name}` to target a specific profile from `~/.aws/credentials` or `~/.aws/config`
3. AWS SSO: run `aws sso login --profile {profile_name}` before invoking if using IAM Identity Center
4. Instance/container role: used automatically if running inside EC2 or ECS

**Required IAM permissions for the caller:**
```
s3:GetObject
s3:ListBucket
s3:GetBucketLogging
```

> If targeting `prod`, ensure your local profile has MFA or SSO session active before invoking.

## Steps

1. **Resolve log location**
   - For `server-access` logs: confirm the target bucket has server access logging enabled
     and identify the destination bucket and prefix
   - For `application` logs: use `bucket_name` and `prefix` directly

2. **Validate environment access**
   - Verify caller has `s3:GetObject` and `s3:ListBucket` on the log bucket
   - If environment is `prod`, emit an audit log entry before fetching (CMP-001)

3. **List matching log objects**
   - Use `aws s3 ls s3://{log_bucket}/{prefix}` scoped to the time window
   - Derive S3 key date prefixes from `start_time` and `end_time` to avoid full bucket scans
   - Stop listing once `limit` objects are identified

4. **Download and parse log objects**
   - Download each log file using `aws s3 cp`
   - **Server access log format**: parse space-delimited fields per
     [AWS S3 server access log format](https://docs.aws.amazon.com/AmazonS3/latest/userguide/LogFormat.html)
     Key fields: `bucket_owner`, `bucket`, `time`, `remote_ip`, `requester`,
     `operation`, `key`, `http_status`, `error_code`, `bytes_sent`, `user_agent`
   - **Application log format**: attempt JSON parse first; fall back to line-by-line

5. **Apply filters**
   - Apply `filter_status`, `filter_key`, `filter_ip` against parsed entries
   - Flag entries with HTTP status 403, 404, 5xx, or error codes
     `AccessDenied`, `NoSuchKey`, `NoSuchBucket`, `SlowDown`

6. **Summarise findings**
   - Total entries parsed
   - Count by HTTP status group (2xx / 3xx / 4xx / 5xx)
   - Top 5 requested keys
   - Top 5 requesters (IAM principal or IP)
   - Any `AccessDenied` or throttling (`SlowDown`) events highlighted

## Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKILL: S3 Logs Fetch
BUCKET: {bucket_name}
LOG TYPE: {log_type}
ENVIRONMENT: {environment}
WINDOW: {start_time} → {end_time}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY:
  Total entries : {n}
  2xx           : {n}
  3xx           : {n}
  4xx           : {n}
  5xx           : {n}

TOP KEYS ACCESSED:
  {key} — {n} requests

TOP REQUESTERS:
  {iam_principal_or_ip} — {n} requests

FLAGGED EVENTS (errors / denied / throttled):
  [{time}] {operation} {key} HTTP={status} ERROR={error_code} IP={ip}
  ...

RAW ENTRIES (most recent first, up to limit):
  [{time}] {operation} {key} {status} {requester}
  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## AWS CLI Commands Reference

```bash
# List log objects by prefix and time window
aws s3 ls s3://{log_bucket}/{prefix} --recursive

# Download a single log file
aws s3 cp s3://{log_bucket}/{log_key} - | head -100

# Sync all logs for a date prefix to local for analysis
aws s3 sync s3://{log_bucket}/{prefix} ./tmp-logs/ --exclude "*" --include "*.log"

# Check if server access logging is enabled on a bucket
aws s3api get-bucket-logging --bucket {bucket_name}

# List objects with metadata (to filter by LastModified)
aws s3api list-objects-v2 \
  --bucket {log_bucket} \
  --prefix {prefix} \
  --query "Contents[?LastModified>='{start_time}']"
```

## Governance Checks Applied
- Audit log written before any prod bucket access (CMP-001)
- PII must not be displayed in output — mask IP addresses in prod summaries if required (CMP-002)
- Read-only operation — no object deletion, modification, or ACL changes permitted
- Access confined to log bucket only — must not traverse to source data bucket (TF-P-003, SP-003)

## Error Handling

| Error | Response |
|---|---|
| Server access logging not enabled | Warn user and provide the AWS CLI command to enable it |
| Access denied on log bucket | Return required IAM permissions: `s3:GetObject`, `s3:ListBucket` |
| No log files in time window | Suggest widening the time range or checking the prefix |
| Log bucket in different region | Remind user to pass `--region` matching the log bucket's region |
| Very large log volume (>1000 files) | Warn user, recommend narrowing prefix or time window, cap at limit |
