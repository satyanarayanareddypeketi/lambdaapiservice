---
name: fetch-governance
description: Fetches governance policies from the central ai-governance repo and caches them locally in .claude/governance-cache/. Run automatically by agents when cache is stale.
---

1. Read .claude/governance-cache/last-updated.txt
   - If date matches today (YYYY-MM-DD) → respond: "Cache is current." and stop.
   - Otherwise → proceed to step 2.

2. Download the entire repo as a zip and extract only the needed files:
   - Download: https://github.com/satyanarayanareddypeketi/ai-governance/archive/refs/heads/main.zip
   - Extract and copy into .claude/governance-cache/ with these names:
     security/policies.md        → security-policies.md
     deployment/policies.md      → deployment-policies.md
     compliance/policies.md      → compliance-policies.md
     cost/policies.md            → cost-policies.md
     github-actions/policies.md  → github-actions-policies.md
     python/policies.md          → python-policies.md
     python/standards.md         → python-standards.md
     terraform/policies.md       → terraform-policies.md
     terraform/standards.md      → terraform-standards.md
     agents/policies.md          → agent-policies.md
     agents/standards.md         → agent-standards.md

3. Write today's date into .claude/governance-cache/last-updated.txt

5. Respond: "Governance policies refreshed. 11 files cached."

Do this silently. If a fetch fails, report which file failed and stop.
