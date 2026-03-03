---
name: update-venue
description: Update a conference/venue's deadline data by researching official sources
allowed-tools: WebSearch, WebFetch, Read, Write, Glob, Grep, Bash
argument-hint: <venue-identifier>
---

# Update Venue Deadline Data

You are an expert at finding and extracting academic conference deadline information from official websites. Work maximally diligently! Think very hard!

## YOUR TASK

You are given a venue identifier via `$ARGUMENTS` (e.g., `fc`, `ccs`, `sp`). Your job is to:
1. Read the current YAML data from `_data/conferences_raw/$ARGUMENTS.yml`
2. Find the OFFICIAL website for the NEXT edition of this conference (if the current data shows year X, look for year X+1, X+2, etc.)
3. Extract accurate deadline information from the official Call for Papers (CFP) page
4. Decide whether an update is needed
5. If yes, write the updated YAML back to `_data/conferences_raw/$ARGUMENTS.yml`
6. Do NOT run `compress-conferences.sh` — leave that as a manual step

**IMPORTANT:** Only return updates if you find official, verifiable information. If you cannot find updated information from an authoritative source, do not update the file.


## DEFINITIONS

- **Venue**: A series of academic conferences/workshops, or a journal (e.g., "ACM CCS" is a venue)
- **Edition**: A specific year's instance of a venue (e.g., "ACM CCS 2026" is an edition of the venue "ACM CCS")
- **Submission Cycle**: A period during which papers can be submitted for a specific edition. Some conferences have multiple cycles per year (e.g., "First cycle", "Spring cycle", "Fall cycle")
- **Deadline**: The earliest date/time by which submissions must be registered or submitted to be considered for a cycle


## INFORMATION SOURCES — CRITICAL RULES

**ONLY use authoritative sources:**
- Official conference websites (e.g., ccs2026.sigsac.org, fc26.ifca.ai)
- Publisher websites (ACM, IEEE, USENIX, IACR official pages)
- Direct links from conference organizers

**NEVER use third-party aggregators:**
- Do NOT trust: wikicfp.com, mpc-deadlines.github.io, sslab.skku.edu, aconf.org, or similar aggregator sites
- If you find info on a third-party site, you MUST locate the official source and verify
- If you cannot verify through official sources, do not use that information


## STEP-BY-STEP PROCEDURE

1. Use `Read` to load `_data/conferences_raw/$ARGUMENTS.yml`
2. Check if the first entry has `inactive: true` — if so, report "Venue is inactive, skipping" and stop
3. Note the current year and edition info in the existing data
4. Use `WebSearch` to search for the next edition's official website (e.g., "ACM CCS 2027 call for papers")
5. Use `WebFetch` to browse the official conference main page and CFP page
6. Extract all deadline information
7. Verify the information is for the correct year and edition
8. If an update is warranted, write the updated YAML to the file using `Write`
9. If no update is needed, report why and stop


## SEARCH STRATEGY

1. Start by searching for the conference name + next year (e.g., "ACM CCS 2027 call for papers")
2. Look for official websites with patterns like:
   - `{conf}{year}.{domain}` (e.g., ccs2027.sigsac.org)
   - `{year}.{conf}.{domain}` (e.g., 2027.ccs.sigsac.org)
   - Official publisher pages (usenix.org, ieee-security.org, etc.)
3. Find the main page of the website
4. From the main page, extract dates / location of the edition
5. Find the "Call for Papers" or "CFP" page (through navigation or search)
6. From the CFP page, extract all detailed deadline information
7. Verify the information is for the correct year and edition
8. Double check all information is correct and complete before producing the new YAML
9. Be skeptical of information in the existing YAML and verify it through official sources; correct it if necessary
10. Make a minimum of 3 search or browsing attempts before concluding that no update is available


## WHEN TO UPDATE

**Write an update if:**
- You find a newer edition (year X+1, X+2, etc.) with official deadline information
- You can verify all information from authoritative sources
- The information is more complete or accurate than what currently exists

**Do NOT update if:**
- No newer edition information is available online
- You cannot find official sources to verify the information
- The existing data is already correct and complete
- You can only find information on third-party aggregator sites but cannot verify it through authoritative sources

CRITICAL: Conclude "no update needed" only after extremely thorough research — minimum 3 search or browsing attempts!


## CONFERENCE DATA SCHEMA

Each conference cycle in the YAML file is a list entry with these fields in this exact order:

1. **id** (string): Unique identifier. Format: `{shortname}{YY}{optional-cycle}`
   - Examples: `ccs26a`, `ccs26b`, `nsdi26spring`, `nsdi26fall`, `eurosp26`, `fc26`
   - Lowercase, no spaces. For cycles: `a`/`b` for first/second, or `spring`/`fall`/`winter` for seasonal

2. **year** (integer): The year of the edition (e.g., 2026)

3. **title** (string): Short name WITHOUT year or edition number
   - Correct: `ACM CCS`, `IEEE S&P`, `FC`, `USENIX NSDI`
   - Wrong: `ACM CCS 2026`, `CCS 26th`, `FC 2026`

4. **full_title** (string): Complete official name WITHOUT year
   - Correct: `ACM Conference on Computer and Communications Security`
   - Wrong: `ACM Conference on Computer and Communications Security 2026`

5. **link** (string): URL to the official CFP page of the edition. Prefer direct CFP links over main venue pages.

6. **deadline** (string): Earliest submission deadline in format `YYYY-MM-DD HH:MM:SS`
   - Use 24-hour format (`23:59:59`, not `11:59:59 PM`)
   - If multiple deadlines exist (e.g., abstract + full paper), use the EARLIEST one
   - Must be quoted in YAML: `'2026-01-14 23:59:59'`

7. **timezone** (string): IANA timezone or Etc/GMT format. Must be from the allowed list below.
   - For "Anywhere on Earth" (AoE) deadlines: use `Etc/GMT+12`
   - Common: `America/New_York`, `America/Los_Angeles`, `Europe/London`, `Etc/GMT+12`

8. **note** (string): Additional deadline and notification information
   - MUST include: cycle name (if multiple cycles), what the `deadline` field represents (if there are multiple deadlines like abstract registration and full paper), and author notification date
   - Format examples:
     - `First cycle. Abstract registration deadline. Full paper deadline 2026-01-14 23:59:59 AoE. Author notification 2026-04-09.`
     - `Abstract registration deadline. Full paper deadline 2025-04-25 23:59:59 PDT. Author notification 2025-07-24.`
     - `Spring cycle. Author notification 2025-07-24.`
     - `Author notification 2025-07-24.`
   - DO NOT include: early-rejection dates, rebuttal deadlines, camera-ready deadlines, workshop/tutorial proposal deadlines, registration deadlines, notes about whether deadlines are firm or extended

9. **place** (string): Location of the edition
   - Format: `City, State, Country` or `City, Country`
   - Examples: `San Francisco, CA, USA`, `The Hague, The Netherlands`
   - Use `TBD` if unknown

10. **date** (string): Human-readable conference dates
    - Format: `Day-Day Month Year` or `Day Month-Day Month Year` (if spanning two months)
    - Use `TBD` if unknown

11. **start** (string): Conference start date as `YYYY-MM-DD`, quoted in YAML
    - Use first day of the year (`YYYY-01-01`) if unknown

12. **end** (string): Conference end date as `YYYY-MM-DD`, quoted in YAML
    - Use last day of the year (`YYYY-12-31`) if unknown

13. **sub** (array): Subject areas. Array of strings from: `BC`, `CR`, `DS`, `SEC`, `EC`
    - BC = blockchain, CR = cryptography, DS = distributed systems, SEC = security, EC = economics/incentives

14. **inactive** (boolean): Set to `false` for active conferences


## MULTIPLE CYCLES HANDLING

If a conference has multiple submission cycles (e.g., first/second cycle, spring/fall cycles):
- Create a SEPARATE list entry for EACH cycle
- Each cycle gets its own `id`, `deadline`, and `note` field
- All cycles share the same `year`, `title`, `full_title`, `link`, `place`, `date`, `start`, `end`, `sub`, `inactive`
- Clearly indicate the cycle in both the `id` field and `note` field


## TIMEZONE HANDLING

- **"Anywhere on Earth" (AoE)**: Always use `Etc/GMT+12` (note the **+** sign!)
- **Time format**: Always use 24-hour format (`23:59:59`, never `11:59:59 PM`)
- **In the note field**: When mentioning additional deadlines, always include the time and timezone abbreviation:
  - Good: `Full paper deadline 2026-01-14 23:59:59 AoE`
  - Good: `Full paper deadline 2025-04-25 23:59:59 PDT`
  - Bad: `Full paper deadline 2026-01-14` (missing time and timezone)


## ALLOWED TIMEZONES

The timezone field must be one of the following values exactly:

`Etc/GMT+12`, `Etc/GMT+11`, `Etc/GMT+10`, `Etc/GMT+9`, `Etc/GMT+8`, `Etc/GMT+7`, `Etc/GMT+6`, `Etc/GMT+5`, `Etc/GMT+4`, `Etc/GMT+3`, `Etc/GMT+2`, `Etc/GMT+1`, `Etc/GMT`, `Etc/GMT-1`, `Etc/GMT-2`, `Etc/GMT-3`, `Etc/GMT-4`, `Etc/GMT-5`, `Etc/GMT-6`, `Etc/GMT-7`, `Etc/GMT-8`, `Etc/GMT-9`, `Etc/GMT-10`, `Etc/GMT-11`, `Etc/GMT-12`, `Etc/UTC`, `Africa/Abidjan`, `Africa/Nairobi`, `Africa/Algiers`, `Africa/Lagos`, `Africa/Khartoum`, `Africa/Cairo`, `Africa/Casablanca`, `Europe/Paris`, `Africa/Johannesburg`, `Africa/Juba`, `Africa/Sao_Tome`, `Africa/Tripoli`, `America/Adak`, `America/Anchorage`, `America/Santo_Domingo`, `America/Fortaleza`, `America/Asuncion`, `America/Panama`, `America/Mexico_City`, `America/Managua`, `America/Caracas`, `America/Lima`, `America/Denver`, `America/Campo_Grande`, `America/Chicago`, `America/Chihuahua`, `America/Ciudad_Juarez`, `America/Phoenix`, `America/Whitehorse`, `America/New_York`, `America/Los_Angeles`, `America/Halifax`, `America/Godthab`, `America/Havana`, `America/Mazatlan`, `America/Metlakatla`, `America/Miquelon`, `America/Noronha`, `America/Ojinaga`, `America/Santiago`, `America/Sao_Paulo`, `America/Scoresbysund`, `America/St_Johns`, `Antarctica/Casey`, `Asia/Bangkok`, `Asia/Vladivostok`, `Australia/Sydney`, `Asia/Tashkent`, `Pacific/Auckland`, `Europe/Istanbul`, `Antarctica/Troll`, `Antarctica/Vostok`, `Asia/Almaty`, `Asia/Amman`, `Asia/Kamchatka`, `Asia/Dubai`, `Asia/Beirut`, `Asia/Dhaka`, `Asia/Kuala_Lumpur`, `Asia/Kolkata`, `Asia/Chita`, `Asia/Shanghai`, `Asia/Colombo`, `Asia/Damascus`, `Europe/Athens`, `Asia/Gaza`, `Asia/Hong_Kong`, `Asia/Jakarta`, `Asia/Jayapura`, `Asia/Jerusalem`, `Asia/Kabul`, `Asia/Karachi`, `Asia/Kathmandu`, `Asia/Sakhalin`, `Asia/Makassar`, `Asia/Manila`, `Asia/Seoul`, `Asia/Rangoon`, `Asia/Tehran`, `Asia/Tokyo`, `Atlantic/Azores`, `Europe/Lisbon`, `Atlantic/Cape_Verde`, `Australia/Adelaide`, `Australia/Brisbane`, `Australia/Darwin`, `Australia/Eucla`, `Australia/Lord_Howe`, `Australia/Perth`, `Pacific/Easter`, `Europe/Dublin`, `Pacific/Tongatapu`, `Pacific/Kiritimati`, `Pacific/Tahiti`, `Pacific/Niue`, `Pacific/Galapagos`, `Pacific/Pitcairn`, `Pacific/Gambier`, `Europe/London`, `Europe/Chisinau`, `Europe/Moscow`, `Europe/Volgograd`, `Pacific/Honolulu`, `Pacific/Chatham`, `Pacific/Apia`, `Pacific/Fiji`, `Pacific/Guam`, `Pacific/Marquesas`, `Pacific/Pago_Pago`, `Pacific/Norfolk`


## YAML OUTPUT FORMAT

The output YAML must follow the exact structure of the existing files. Key rules:

- Field order must match the schema order above (id, year, title, full_title, link, deadline, timezone, note, place, date, start, end, sub, inactive)
- `deadline`, `start`, and `end` values must be quoted with single quotes (e.g., `'2026-01-14 23:59:59'`)
- `sub` is a YAML array (use `- BC` style, one per line)
- `inactive` is a bare boolean (`false` or `true`, not quoted)
- Multiple cycles are separate list entries at the top level (first entry starts with `- id:`, subsequent entries start with `- id:`)
- Preserve 2-space indentation for fields within each entry
- No trailing whitespace

Example single-cycle file:
```yaml
- id: fc27
  year: 2027
  title: FC
  full_title: Financial Cryptography and Data Security
  link: https://fc27.ifca.ai/cfp.html
  deadline: '2026-09-15 23:59:59'
  timezone: Etc/GMT+12
  note: Author notification 2026-11-20.
  place: Somewhere, Country
  date: 2-6 March 2027
  start: '2027-03-02'
  end: '2027-03-06'
  sub:
  - BC
  inactive: false
```

Example multi-cycle file:
```yaml
- id: ccs27a
  year: 2027
  title: ACM CCS
  full_title: ACM Conference on Computer and Communications Security
  link: https://www.sigsac.org/ccs/CCS2027/cfp.html
  deadline: '2027-01-10 23:59:59'
  timezone: Etc/GMT+12
  note: First cycle. Abstract submission deadline. Full paper deadline 2027-01-17 23:59:59
    AoE. Author notification 2027-04-10.
  place: City, Country
  date: November 10-14, 2027
  start: '2027-11-10'
  end: '2027-11-14'
  sub:
  - SEC
  - DS
  inactive: false
- id: ccs27b
  year: 2027
  title: ACM CCS
  full_title: ACM Conference on Computer and Communications Security
  link: https://www.sigsac.org/ccs/CCS2027/cfp.html
  deadline: '2027-04-25 23:59:59'
  timezone: Etc/GMT+12
  note: Second cycle. Abstract submission deadline. Full paper deadline 2027-05-02 23:59:59
    AoE. Author notification 2027-07-20.
  place: City, Country
  date: November 10-14, 2027
  start: '2027-11-10'
  end: '2027-11-14'
  sub:
  - SEC
  - DS
  inactive: false
```


## PRE-WRITE VERIFICATION CHECKLIST

Before writing the updated YAML file, verify ALL of the following:

- [ ] `id` follows the `{shortname}{YY}{cycle}` pattern, lowercase, no spaces
- [ ] `year` is an integer, not quoted
- [ ] `title` does NOT contain the year or edition number
- [ ] `full_title` does NOT contain the year
- [ ] `link` is a valid URL pointing to the official conference/CFP page
- [ ] `deadline` is in `'YYYY-MM-DD HH:MM:SS'` format (quoted, 24-hour time)
- [ ] `timezone` is from the allowed list above
- [ ] For AoE (anywhere on earth) deadlines: timezone is `Etc/GMT+12` (with **+**, not `-`)
- [ ] `note` includes cycle name (if multi-cycle), deadline type (if multi-deadline), and author notification date
- [ ] `note` does NOT include camera-ready, rebuttal, registration, or workshop deadlines
- [ ] Additional deadlines in `note` include time and timezone
- [ ] `place` uses proper format (`City, State, Country` or `City, Country`)
- [ ] `date` is human-readable
- [ ] `start` and `end` are in `'YYYY-MM-DD'` format (quoted)
- [ ] `sub` contains only valid codes: `BC`, `CR`, `DS`, `SEC`, `EC`
- [ ] `inactive` is `false` (bare boolean)
- [ ] Field order matches the schema
- [ ] Each cycle is a separate top-level list entry
- [ ] All 14 fields are present for each entry


## COMMON MISTAKES TO AVOID

1. **Including year in title**: Wrong: `ACM CCS 2026`, Right: `ACM CCS`
2. **Wrong date format**: Wrong: `2026/11/15`, Right: `'2026-11-15'` (for start/end)
3. **Missing time or timezone in note**: Wrong: `Full paper deadline 2026-01-14`, Right: `Full paper deadline 2026-01-14 23:59:59 AoE`
4. **Using 12-hour format**: Wrong: `11:59:59 PM`, Right: `23:59:59`
5. **Including wrong info in note**: Don't include camera-ready, rebuttal, or registration deadlines
6. **Wrong timezone for AoE**: Wrong: `Etc/GMT-12`, Right: `Etc/GMT+12` (note the + sign!)
7. **Mixing cycles**: Each cycle must be a separate list entry with unique id
8. **Using third-party sources**: Always verify through official conference websites
9. **Incorrect field order**: Follow the exact order specified in the schema
10. **Missing required fields**: All 14 fields must be present for each entry
11. **Unquoted deadline/start/end**: These must be single-quoted in YAML
12. **Forgetting the `inactive` field**: Always include `inactive: false`