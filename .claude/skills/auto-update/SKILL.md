---
name: auto-update
description: Scan all venues for outdated deadlines and update them via /update-venue
allowed-tools: Skill, Read, Glob, Bash, Agent
argument-hint: "[venue1 venue2 ...] (optional, defaults to all)"
---

# Auto-Update All Venues

Scan conference venues for outdated data and invoke `/update-venue` for each venue that needs updating. This replaces the batch-processing logic formerly in `chatgpt-updater.py`.

## YOUR TASK

You are given an optional list of venue identifiers via `$ARGUMENTS` (e.g., `fc ccs sp`). If no arguments are provided, process ALL venues in `_data/conferences_raw/`.

Your job is to:
1. Identify which venues need updating
2. Invoke `/update-venue` for each one
3. Run `compress-conferences.sh` at the end

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

### Step 4: Update venues

For each venue classified as **UPDATE**, invoke the `/update-venue` skill using the `Skill` tool:

```
Skill: update-venue
Args: {venue-identifier}
```

Process venues **one at a time** and report the outcome of each update (updated / no update available / error).

### Step 5: Run compress-conferences.sh

After all venue updates are complete, run:

```bash
./compress-conferences.sh
```

This regenerates `_data/conferences.yml` from the individual YAML files.

### Step 6: Final summary

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

- **Do NOT modify any YAML files directly** — that's the job of `/update-venue`.
- **Do NOT skip the triage step** — it avoids unnecessary web searches for venues that are clearly still current.
- **Process updates sequentially**, not in parallel, to avoid overwhelming web sources and to keep output readable.
- **Always run `compress-conferences.sh`** at the end, even if no venues were updated (it's idempotent).