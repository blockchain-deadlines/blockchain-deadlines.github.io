---
name: auto-update
description: Scan all venues for outdated deadlines and update them via /update-venue
allowed-tools: Skill, Read, Glob, Bash, Agent
argument-hint: "[venue1 venue2 ...] (optional, defaults to all)"
---

# Auto-Update All Venues

Scan conference venues for outdated data and update each one that needs it. Uses parallel agents for efficient processing, with each venue update running in its own context window.

## YOUR TASK

You are given an optional list of venue identifiers via `$ARGUMENTS` (e.g., `fc ccs sp`). If no arguments are provided, process ALL venues in `_data/conferences_raw/`.

Your job is to:
1. Identify which venues need updating (triage)
2. Launch agents in parallel batches to update them
3. Review agent results and fix any issues
4. Run `compress-conferences.sh` at the end

## PROCEDURE

### Step 1: Build the venue list

- If `$ARGUMENTS` is non-empty, split it by whitespace to get the list of venue identifiers. Each identifier corresponds to `_data/conferences_raw/{identifier}.yml`.
- If `$ARGUMENTS` is empty, use `Glob` to list all `_data/conferences_raw/*.yml` files and extract the venue identifiers (filename without `.yml`).

### Step 2: Triage each venue

For each venue, use `Read` to load its YAML file and determine its status. Classify each venue into one of these categories:

1. **SKIP (inactive)**: The first entry has `inactive: true`. Do not update.
2. **SKIP (upcoming)**: The last cycle's conference end date (`end` field) is in the future AND the last cycle's deadline is in the future. The data is still current — no update needed.
3. **UPDATE (past deadline)**: The last cycle's deadline is in the past (all submission windows have closed). This venue should be checked for a newer edition.
4. **UPDATE (past conference)**: The last cycle's conference end date (`end` field) is in the past. The conference is over and a newer edition may be available.

When a venue has multiple cycles, use the LAST cycle's deadline and end date for triage (since that represents the latest relevant date).

**Today's date should be determined from the system context (the `currentDate` provided in the conversation).**

### Step 3: Report triage results

Before starting updates, print a summary table of all venues and their triage status:

```
## Venue Triage Summary

| Venue | Status | Last Deadline | Conference End | Action |
|-------|--------|---------------|----------------|--------|
| fc    | Past conference | 2025-09-16 | 2026-03-06 | UPDATE |
| sp    | Upcoming | 2025-11-06 | 2026-05-21 | SKIP |
| cbt   | Inactive | — | — | SKIP |
| ...   | ... | ... | ... | ... |

Venues to update: fc, ccs, disc, ...
```

### Step 4: Update venues using parallel agents

Launch venue updates using the `Agent` tool with `subagent_type: "general-purpose"`. Process venues in **parallel batches of 4-6 agents** at a time to balance speed with resource usage.

For each agent, provide a detailed prompt that includes:
1. The venue identifier
2. Instructions to invoke `/update-venue {venue}` using the `Skill` tool
3. Instructions to report whether the venue was updated, had no update available, or encountered an error

**Agent prompt template:**

```
Invoke the /update-venue skill for the venue "{venue}" by calling the Skill tool with skill="update-venue" and args="{venue}".

After the skill completes, report:
- Whether the venue was UPDATED (and to what edition/year)
- Or NO UPDATE AVAILABLE (and why)
- Or ERROR (and what went wrong)
```

**Batching strategy:**
- Launch 4-6 agents in a single message (they run in parallel)
- Wait for all agents in the batch to complete
- Report results from the batch
- Launch the next batch
- Continue until all venues are processed

### Step 5: Review agent results

After each batch completes:
1. Read the result from each agent
2. Verify the changes look correct (check the modified YAML files against the specification of the /update-venue skill)
3. Fix any issues (e.g., agents that incorrectly set `inactive: true` — this flag is ONLY for discontinued venues, never for past deadlines)
4. Report the outcome for each venue

### Step 6: Run compress-conferences.sh

After all venue updates are complete, run:

```bash
./compress-conferences.sh
```

This regenerates `_data/conferences.yml` from the individual YAML files.

### Step 7: Final summary

Print a final summary of what was done:

```
## Update Summary

| Venue | Result |
|-------|--------|
| fc    | Updated to FC 2027 |
| ccs   | No update available |
| disc  | Updated to DISC 2027 |
| ...   | ... |

Total: X venues updated, Y no update available, Z skipped (inactive/upcoming)
compress-conferences.sh executed successfully.
```

## IMPORTANT NOTES

- **Do NOT modify any YAML files directly** — that's the job of `/update-venue` (invoked via agents).
- **Do NOT skip the triage step** — it avoids unnecessary web searches for venues that are clearly still current.
- **Use parallel agents** for venue updates — each agent gets its own context window, preventing context bloat when processing many venues.
- **Review agent results** — agents may make mistakes (like incorrectly setting `inactive: true`). Always check changes.
- **Always run `compress-conferences.sh`** at the end, even if no venues were updated (it's idempotent).
- The `inactive` flag means a venue series is **discontinued**. It does NOT mean "the deadline has passed." Never set `inactive: true` just because a deadline is in the past.
