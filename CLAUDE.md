# CLAUDE.md

This file is automatically read by Claude Code when you open this project.

## Project Overview
This repo was scaffolded by DevPipeline Studio with a GitHub Actions CI/CD pipeline,
Lambda function code, Terraform infrastructure, and AI-powered agents and skills.

## Active Agents
Agents are located in `.claude/agents/`. Each agent has a specific role in the pipeline.

### CodeGuardian
- File: `.claude/agents/CodeGuardian.md`
- Read this file to understand the agent's purpose and instructions.

### TestSentinel
- File: `.claude/agents/TestSentinel.md`
- Read this file to understand the agent's purpose and instructions.

### DeployAssure
- File: `.claude/agents/DeployAssure.md`
- Read this file to understand the agent's purpose and instructions.

### PipelineAssist
- File: `.claude/agents/PipelineAssist.md`
- Read this file to understand the agent's purpose and instructions.

### IncidentTracer
- File: `.claude/agents/IncidentTracer.md`
- Read this file to understand the agent's purpose and instructions.


## Available Skills
Skills are located in `.claude/commands/`. Each skill is a slash command you can invoke in Claude Code.

### LambdaLogFetch
- File: `.claude/commands/lambda-logs-fetch.md`
- Use as a slash command: `/lambdalogfetch`

### S3LogFetch
- File: `.claude/commands/s3-logs-fetch.md`
- Use as a slash command: `/s3logfetch`

### GitHubActionLogFetch
- File: `.claude/commands/github-actions-debug.md`
- Use as a slash command: `/githubactionlogfetch`


## Governance Policy Refresh

At the start of every agent invocation, run the `fetch-governance` command silently before proceeding.
The command handles staleness check, fetching, caching, and updating the timestamp automatically.

## Token Efficiency

- Each agent reads only the governance files relevant to its domain — not all files
- Limit log/file reads to 50 lines max unless explicitly asked for more
- Respond in one turn — no follow-up questions unless critical information is missing

## Project Structure
```
.claude/
  agents/            # AI agent instruction files
  commands/          # Claude Code slash commands (skills)
  governance-cache/  # Locally cached governance policy files (auto-refreshed daily)
.github/
  workflows/         # GitHub Actions CI/CD pipeline
terraform/           # Infrastructure as code
tests/               # Unit tests
lambda_function.py   # AWS Lambda handler
```

## Pipeline Stages
1. Build
2. Unit Test
3. Security Scan
4. Package
5. Deploy
