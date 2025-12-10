#! /usr/bin/env python3

import os
import requests
import json
import yaml
import copy
import time
import ssl
from datetime import datetime
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError
from typing import Literal, Optional
from openai import OpenAI
import typer


PROMPT = """
You are an expert at finding and extracting academic conference deadline information from official websites.

Today's date: [[CURRENT DATE HERE]]

# YOUR TASK

The user will provide you with YAML data about an academic conference (venue) that is (quite possibly) OUTDATED. Your job is to:
1. Find the OFFICIAL website for the NEXT edition of this conference (if the user provides year X, look for year X+1, X+2, etc.)
2. Extract accurate deadline information from the official Call for Papers (CFP) page
3. Return updated YAML data in the exact format specified below

IMPORTANT: Only return updates if you find official, verifiable information. If you cannot find updated information from an authoritative source, return `any_updates: false`.


# DEFINITIONS

- **Venue**: A series of academic conferences/workshops (e.g., "ACM CCS" is a venue)
- **Edition**: A specific year's instance of a venue (e.g., "ACM CCS 2026" is an edition)
- **Submission Cycle**: A period during which papers can be submitted for a specific edition. Some conferences have multiple cycles per year (e.g., "First cycle", "Spring cycle", "Fall cycle")
- **Deadline**: The earliest date/time by which submissions must be registered or submitted for a cycle


# INFORMATION SOURCES - CRITICAL RULES

**ONLY use authoritative sources:**
- Official conference websites (e.g., ccs2026.sigsac.org, fc26.ifca.ai)
- Publisher websites (ACM, IEEE, USENIX, IACR official pages)
- Direct links from conference organizers

**NEVER use third-party aggregators:**
- Do NOT trust: wikicfp.com, mpc-deadlines.github.io, sslab.skku.edu, aconf.org, or similar aggregator sites
- If you find info on a third-party site, you MUST locate the official source and verify
- If you cannot verify through official sources, return `any_updates: false`


# REQUIRED OUTPUT FORMAT

You must return a JSON object with this structure:
{
  "any_updates": true/false,
  "conferences": [array of conference objects]
}

Each conference object represents ONE submission cycle and must have these fields in this exact order:

1. **id** (string, REQUIRED): Unique identifier for this cycle. Format: `{shortname}{year}{cycle}` 
   - Examples: `ccs26a`, `ccs26b`, `nsdi26spring`, `nsdi26fall`, `eurosp26`, `fc26`
   - Use lowercase, no spaces. For cycles: `a`/`b` for first/second, or `spring`/`fall`/`winter` for seasonal

2. **year** (integer, REQUIRED): The year of the conference edition (e.g., 2026)

3. **title** (string, REQUIRED): Short name WITHOUT year or edition number
   - Correct: "ACM CCS", "IEEE S&P", "FC", "USENIX NSDI"
   - Wrong: "ACM CCS 2026", "CCS 26th", "FC 2026"

4. **full_title** (string, REQUIRED): Complete official name WITHOUT year
   - Correct: "ACM Conference on Computer and Communications Security"
   - Wrong: "ACM Conference on Computer and Communications Security 2026"

5. **link** (string, REQUIRED): URL to the official CFP page where deadline info was found
   - Must be the exact page containing the deadline information
   - Prefer direct CFP links over main conference pages

6. **deadline** (string, REQUIRED): Earliest submission deadline in format 'YYYY-MM-DD HH:MM:SS'
   - Use 24-hour format (23:59:59, not 11:59:59 PM)
   - If multiple deadlines exist (e.g., abstract + full paper), use the EARLIEST one
   - Format: '2026-01-14 23:59:59' (with quotes in YAML)

7. **timezone** (string, REQUIRED): IANA timezone name or Etc/GMT format
   - For "Anywhere on Earth" (AoE) deadlines: use `Etc/GMT+12`
   - Common timezones: `America/New_York`, `America/Los_Angeles`, `Europe/London`, `Etc/GMT+12`
   - Must be a valid timezone from the allowed list

8. **note** (string, REQUIRED): Additional deadline and notification information
   - MUST include: cycle name (if multiple cycles), what the `deadline` field represents, other deadlines, author notification date
   - Format examples:
     - "First cycle. Abstract registration deadline. Full paper deadline 2026-01-14 23:59:59 AoE. Author notification 2026-04-09."
     - "Spring cycle. Abstract registration deadline. Full paper deadline 2025-04-25 23:59:59 PDT. Author notification 2025-07-24."
     - "Author notification 2025-11-24." (if only one deadline)
   - DO NOT include: early-rejection dates, rebuttal deadlines, camera-ready deadlines, workshop proposals, tutorial deadlines, registration deadlines, or "firm deadline" notes, etc.

9. **place** (string, REQUIRED): Location where conference will be held
   - Format: "City, State, Country" or "City, Country"
   - Examples: "San Francisco, CA, USA", "The Hague, The Netherlands", "St. Kitts Marriott Resort, St. Kitts"

10. **date** (string, REQUIRED): Human-readable conference dates
    - Format: "Day-Day Month Year" or "Day Month-Day Month Year"

11. **start** (string, REQUIRED): Conference start date in format 'YYYY-MM-DD'
    - Format: '2026-11-15' (with quotes in YAML)

12. **end** (string, REQUIRED): Conference end date in format 'YYYY-MM-DD'
    - Format: '2026-11-19' (with quotes in YAML)

13. **sub** (array, REQUIRED): Subject areas. Must be array of strings from: ["BC", "CR", "DS", "SEC", "EC"]
    - BC = blockchain
    - CR = cryptography  
    - DS = distributed systems
    - SEC = security
    - EC = economics/incentives
    - Format: ["SEC", "DS"] or ["BC"]

14. **inactive** (boolean, REQUIRED): Set to `false` for active conferences


# MULTIPLE CYCLES HANDLING

If a conference has multiple submission cycles (e.g., first/second cycle, spring/fall cycles):
- Create a SEPARATE conference object for EACH cycle
- Each cycle gets its own `id`, `deadline`, and `note` field
- All cycles share the same `year`, `title`, `full_title`, `link`, `place`, `date`, `start`, `end`, `sub`
- Clearly indicate the cycle in both the `id` field and `note` field


# TIMEZONE HANDLING - CRITICAL

- **"Anywhere on Earth" (AoE)**: Always use `Etc/GMT+12` as timezone
- **Time format**: Always use 24-hour format (23:59:59, never 11:59:59 PM)
- **Conversion**: If source says "11:59 PM EDT", convert to "23:59:59" and timezone "America/New_York"
- **In note field**: When mentioning additional deadlines, always include timezone:
  - Good: "Full paper deadline 2026-01-14 23:59:59 AoE"
  - Good: "Full paper deadline 2025-04-25 23:59:59 PDT"
  - Bad: "Full paper deadline 2026-01-14" (missing time and timezone)


# SEARCH STRATEGY

1. Start by searching for the conference name + year (e.g., "ACM CCS 2026")
2. Look for official websites with patterns like:
   - {conf}{year}.{domain} (e.g., ccs2026.sigsac.org)
   - {year}.{conf}.{domain} (e.g., 2026.ccs.sigsac.org)
   - Official publisher pages (usenix.org, ieee-security.org, etc.)
3. Navigate to the "Call for Papers" or "CFP" page
4. Extract all deadline information from that page
5. Verify the information is for the correct year and edition


# WHEN TO RETURN UPDATES

Return `any_updates: true` if:
- You find a newer edition (year X+1, X+2, etc.) with official deadline information
- You can verify all information from authoritative sources
- The information is more complete or accurate than what the user provided

Return `any_updates: false` if:
- No newer edition information is available online
- You cannot find official sources to verify the information
- The information you find is not more up-to-date than what the user provided
- You can only find information on third-party aggregator sites

CRITICAL: Return `any_updates: false` only after thorough research and verification (at least 5 search or browsing attempts)!


# TOOLS

You have access to web search and browsing tools. Prefer `callback_browse_text` over `callback_browse_html` when possible, as text content is cheaper. Use tools to:
1. Search for the conference website
2. Browse the main conference page
3. Navigate to and read the CFP page
4. Verify information from official sources only


# EXAMPLES

See the examples provided below to understand the exact format and structure expected.
""".replace("[[CURRENT DATE HERE]]", datetime.now().strftime("%B %d, %Y"))

PROMPT += """
# EXAMPLES - STUDY THESE CAREFULLY

Below are correctly formatted examples. Notice:
- Each submission cycle is a separate entry (see ACM CCS and USENIX NSDI examples)
- Field order is consistent: id, year, title, full_title, link, deadline, timezone, note, place, date, start, end, sub, inactive
- Titles never include years or edition numbers
- Deadlines use 24-hour format with proper timezone
- Note field clearly describes what deadline is used and includes all relevant deadlines + notification date
- IDs follow consistent patterns (shortname + year + cycle identifier)


# COMMON MISTAKES TO AVOID

1. **Including year in title**: Wrong: "ACM CCS 2026", Right: "ACM CCS"
2. **Wrong date format**: Wrong: "2026/11/15", Right: "2026-11-15" (for start/end) or "November 15-19, 2026" (for date)
3. **Missing timezone in note**: Wrong: "Full paper deadline 2026-01-14", Right: "Full paper deadline 2026-01-14 23:59:59 AoE"
4. **Using 12-hour format**: Wrong: "11:59:59 PM", Right: "23:59:59"
5. **Including wrong info in note**: Don't include camera-ready, rebuttal, or registration deadlines
6. **Wrong timezone for AoE**: Wrong: "Etc/GMT-12", Right: "Etc/GMT+12" (note the + sign!)
7. **Mixing cycles**: Each cycle must be a separate conference object with unique id
8. **Using third-party sources**: Always verify through official conference websites
9. **Incorrect field order**: Follow the exact order specified in the format section
10. **Missing required fields**: All 14 fields must be present for each conference object
"""

EXAMPLES = """
- - title: IEEE EuroS&P
    year: 2025
    id: eurosp25
    full_title: IEEE European Symposium on Security and Privacy
    link: https://www.eurosp2025.ieee-security.org/
    deadline: '2024-10-21 23:59:59'
    timezone: Etc/GMT+12
    note: Abstract registration deadline. Full paper deadline 2024-10-24 23:59:59 AoE. Author notification 2025-02-13.
    place: Venice, Italy
    date: June 30 - July 4, 2025
    start: 2025-06-30
    end: 2025-07-04
    sub: [DS, SEC]

- - title: ACM CCS
    full_title: ACM Conference on Computer and Communications Security
    year: 2024
    id: ccs24a
    note: First cycle. Author notification 2024-04-03.
    link: https://www.sigsac.org/ccs/CCS2024/
    deadline: '2024-01-28 23:59:59'
    timezone: Etc/GMT+12
    place: Salt Lake City, Utah, USA
    date: October 14-18, 2024
    start: 2024-10-14
    end: 2024-10-18
    sub: [SEC, DS]

  - title: ACM CCS
    full_title: ACM Conference on Computer and Communications Security
    year: 2024
    id: ccs24b
    note: Second cycle. Author notification 2024-07-04.
    link: https://www.sigsac.org/ccs/CCS2024/
    deadline: '2024-04-29 23:59:59'
    timezone: Etc/GMT+12
    place: Salt Lake City, Utah, USA
    date: October 14-18, 2024
    start: 2024-10-14
    end: 2024-10-18
    sub: [SEC, DS]

- - title: USENIX NSDI
    year: 2025
    full_title: USENIX Symposium on Networked Systems Design and Implementation
    id: nsdi25spring
    link: https://www.usenix.org/conference/nsdi25/
    deadline: '2024-04-30 23:59:59'
    note: Spring cycle. Abstract registration deadline. Full paper deadline 2024-05-07 23:59:59 EDT. Author notification 2024-07-24.
    timezone: America/New_York
    place: Philadelphia, PA, USA
    date: April 28-30, 2025
    start: 2025-04-28
    end: 2025-04-30
    sub: [DS, SEC]

  - title: USENIX NSDI
    year: 2025
    full_title: USENIX Symposium on Networked Systems Design and Implementation
    id: nsdi25fall
    link: https://www.usenix.org/conference/nsdi25/
    deadline: '2024-09-12 23:59:59'
    note: Fall cycle. Abstract registration deadline. Full paper deadline 2024-09-19 23:59:59 EDT. Author notification 2024-12-10.
    timezone: America/New_York
    place: Philadelphia, PA, USA
    date: April 28-30, 2025
    start: 2025-04-28
    end: 2025-04-30
    sub: [DS, SEC]

- - title: FC
    year: 2025
    id: fc25
    full_title: Financial Cryptography and Data Security
    link: https://fc25.ifca.ai
    deadline: '2024-10-11 23:59:59'
    timezone: Etc/GMT+12
    note: Author notification 2024-12-06.
    place: Hotel Shigira Mirage, Miyakojima, Japan
    date: 14-18 April 2025
    start: 2025-04-14
    end: 2025-04-18
    sub: [BC]

- - id: fc26
    year: 2026
    title: FC
    full_title: Financial Cryptography and Data Security
    link: https://fc26.ifca.ai/cfp.html
    deadline: '2025-09-16 23:59:59'
    timezone: Etc/GMT+12
    note: Author notification 2025-11-24.
    place: St. Kitts Marriott Resort, St. Kitts
    date: 2-6 March 2026
    start: 2026-03-02
    end: 2026-03-06
    sub: [BC]

- - title: AFT
    year: 2024
    id: aft24
    full_title: Advances in Financial Technologies
    link: https://aftconf.github.io/aft24/index.html
    deadline: '2024-05-15 23:59:59'
    timezone: Etc/GMT+12
    note: Abstract registration deadline. Full paper deadline 2024-05-22 23:59:59 AoE. Author notification 2024-07-03.
    place: Vienna, Austria
    date: September 23-25, 2024
    start: 2024-09-23
    end: 2024-09-25
    sub: [BC]

- - title: AFT
    year: 2025
    id: aft25
    full_title: Advances in Financial Technologies
    link: https://aftconf.github.io/aft25/CFP.html
    deadline: '2025-05-28 23:59:59'
    timezone: Etc/GMT+12
    note: Full paper deadline. Author notification 2025-07-16.
    place: Carnegie Mellon University, Pittsburgh, PA, USA
    date: October 8-10, 2025
    start: 2025-10-08
    end: 2025-10-10
    sub: [BC]

- - id: sp2026first
    year: 2026
    title: IEEE S&P
    full_title: IEEE Symposium on Security and Privacy
    link: https://sp2026.ieee-security.org/cfpapers.html
    deadline: '2025-05-29 23:59:59'
    timezone: Etc/GMT+12
    note: First cycle. Abstract registration deadline. Full paper deadline 2025-06-05 23:59:59 AoE. Author notification 2025-09-09.
    place: San Francisco, CA, USA
    date: May 18-21, 2026
    start: 2026-05-18
    end: 2026-05-21
    sub: [SEC]
    inactive: false

  - id: sp2026second
    year: 2026
    title: IEEE S&P
    full_title: IEEE Symposium on Security and Privacy
    link: https://sp2026.ieee-security.org/cfpapers.html
    deadline: '2025-11-06 23:59:59'
    timezone: Etc/GMT+12
    note: Second cycle. Abstract registration deadline. Full paper deadline 2025-11-13 23:59:59 AoE. Author notification 2026-03-19.
    place: San Francisco, CA, USA
    date: May 18-21, 2026
    start: 2026-05-18
    end: 2026-05-21
    sub: [SEC]
    inactive: false
"""

PROMPT_REFRESH = """
Refresh requested: Treat the user-provided deadline information as potentially unreliable. Re-verify all details of the provided information from official sources before returning it as an update or indicating that no update is needed. You may assume that the `full_title` and `year` fields are correct and should not be changed.
"""


def callback_search(query: str, serper_api_key: str) -> str:
    # print(">>> callback_search", query)

    url = "https://google.serper.dev/search"
    if not serper_api_key:
        raise RuntimeError("SERPER API key not provided. Use --api-key-serper or set API_KEY_SERPER.")
    payload = json.dumps({
        "q": query,
        "num": 5
    })
    headers = {
        "X-API-KEY": serper_api_key,
        "Content-Type": "application/json"
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    results = response.json()

    returns = ""

    if "answerBox" in results:
        returns += f"# HIGHLIGHT: {results['answerBox'].get('title', '')}\n"
        returns += f"\"{results['answerBox'].get('snippet', '')}\"\n"
        returns += f"\"{results['answerBox'].get('snippetHighlighted', '')}\"\n"
        returns += f"{results['answerBox'].get('link', '')}\n"

    for result in results["organic"]:
        if returns != "":
            returns += "\n"
        
        returns += f"# {result.get('title', '')}\n"
        returns += f"\"{result.get('snippet', '')}\"\n"
        returns += f"{result.get('link', '')}\n"

        if "sitelinks" in result:
            for sitelink in result["sitelinks"]:
                returns += f"- {sitelink.get('title', '')} -> {sitelink.get('link', '')}\n"
    
    return returns

def _retrieve_url(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("WARNING: HTTP ERROR: " + str(e))
        return "HTTP ERROR: " + str(e)
    except (requests.exceptions.SSLError, ssl.SSLCertVerificationError) as e:
        print("WARNING: SSL/HTTPS ERROR: " + str(e))
        return "SSL/HTTPS ERROR: " + str(e)
    except requests.exceptions.ConnectionError as e:
        print("WARNING: CONNECTION ERROR: " + str(e))
        return "CONNECTION ERROR: " + str(e)

    return response.text

def _guard_max_return_length(text: str) -> str:
    callback_max_return_length = 50000

    if len(text) <= callback_max_return_length:
        return text
    else:
        print(f"WARNING: Content exceeds maximum allowed length ({callback_max_return_length} bytes)! Try requesting text rather than HTML!")
        return f"ERROR: Content exceeds maximum allowed length ({callback_max_return_length} bytes)! Try requesting text rather than HTML!"

def callback_browse_html(url: str) -> str:
    text = _retrieve_url(url)

    text = text.replace("\n", " ")
    while "  " in text:
        text = text.replace("  ", " ")
    text = text.strip()
    
    return _guard_max_return_length(text)

def callback_browse_text(url: str) -> list[str]:
    html = _retrieve_url(url)

    soup = BeautifulSoup(html, "html.parser")
    text = "\n\n".join(list(soup.stripped_strings))
    while "  " in text:
        text = text.replace("  ", " ")
    text = text.strip()

    return _guard_max_return_length(text)

tools = [
    {
        "type": "function",
        "function": {
            "name": "callback_search",
            "description": "Search the web for information. Call this and provide a search query whenever you need to search the web for information. Idempotent, do not call repeatedly with the same query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to search the web for information. Case insensitive. Small variations of the query usually return very similar results.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "callback_browse_html",
            "description": "Get HTML content of a website via the http or https URL. Call this and provide a URL whenever you want to retrieve the HTML content of a web page. This function provides more detailed input than callback_browse_text, but is also more expensive, so use it only when necessary. Idempotent, do not call repeatedly with the same URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to browse.",
                    },
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "callback_browse_text",
            "description": "Get text content of a website via the http or https URL. Call this and provide a URL whenever you want to retrieve the text content of a web page. This function provides less detailed input than callback_browse_html, but is also cheaper, so use it when possible. Idempotent, do not call repeatedly with the same URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to browse.",
                    },
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    }
]


class Conference(BaseModel):
    id: str
    year: int
    title: str
    full_title: str
    link: str
    deadline: str
    timezone: Literal["Etc/GMT+12", "Etc/GMT+11", "Etc/GMT+10", "Etc/GMT+9", "Etc/GMT+8", "Etc/GMT+7", "Etc/GMT+6", "Etc/GMT+5", "Etc/GMT+4", "Etc/GMT+3", "Etc/GMT+2", "Etc/GMT+1", "Etc/GMT", "Etc/GMT-1", "Etc/GMT-2", "Etc/GMT-3", "Etc/GMT-4", "Etc/GMT-5", "Etc/GMT-6", "Etc/GMT-7", "Etc/GMT-8", "Etc/GMT-9", "Etc/GMT-10", "Etc/GMT-11", "Etc/GMT-12", "Etc/UTC", "Africa/Abidjan", "Africa/Nairobi", "Africa/Algiers", "Africa/Lagos", "Africa/Khartoum", "Africa/Cairo", "Africa/Casablanca", "Europe/Paris", "Africa/Johannesburg", "Africa/Juba", "Africa/Sao_Tome", "Africa/Tripoli", "America/Adak", "America/Anchorage", "America/Santo_Domingo", "America/Fortaleza", "America/Asuncion", "America/Panama", "America/Mexico_City", "America/Managua", "America/Caracas", "America/Lima", "America/Denver", "America/Campo_Grande", "America/Chicago", "America/Chihuahua", "America/Ciudad_Juarez", "America/Phoenix", "America/Whitehorse", "America/New_York", "America/Los_Angeles", "America/Halifax", "America/Godthab", "America/Havana", "America/Mazatlan", "America/Metlakatla", "America/Miquelon", "America/Noronha", "America/Ojinaga", "America/Santiago", "America/Sao_Paulo", "America/Scoresbysund", "America/St_Johns", "Antarctica/Casey", "Asia/Bangkok", "Asia/Vladivostok", "Australia/Sydney", "Asia/Tashkent", "Pacific/Auckland", "Europe/Istanbul", "Antarctica/Troll", "Antarctica/Vostok", "Asia/Almaty", "Asia/Amman", "Asia/Kamchatka", "Asia/Dubai", "Asia/Beirut", "Asia/Dhaka", "Asia/Kuala_Lumpur", "Asia/Kolkata", "Asia/Chita", "Asia/Shanghai", "Asia/Colombo", "Asia/Damascus", "Europe/Athens", "Asia/Gaza", "Asia/Hong_Kong", "Asia/Jakarta", "Asia/Jayapura", "Asia/Jerusalem", "Asia/Kabul", "Asia/Karachi", "Asia/Kathmandu", "Asia/Sakhalin", "Asia/Makassar", "Asia/Manila", "Asia/Seoul", "Asia/Rangoon", "Asia/Tehran", "Asia/Tokyo", "Atlantic/Azores", "Europe/Lisbon", "Atlantic/Cape_Verde", "Australia/Adelaide", "Australia/Brisbane", "Australia/Darwin", "Australia/Eucla", "Australia/Lord_Howe", "Australia/Perth", "Pacific/Easter", "Europe/Dublin", "Pacific/Tongatapu", "Pacific/Kiritimati", "Pacific/Tahiti", "Pacific/Niue", "Pacific/Galapagos", "Pacific/Pitcairn", "Pacific/Gambier", "Europe/London", "Europe/Chisinau", "Europe/Moscow", "Europe/Volgograd", "Pacific/Honolulu", "Pacific/Chatham", "Pacific/Apia", "Pacific/Fiji", "Pacific/Guam", "Pacific/Marquesas", "Pacific/Pago_Pago", "Pacific/Norfolk"]
    note: str
    place: str
    date: str
    start: str
    end: str
    sub: list[Literal["BC", "CR", "DS", "SEC", "EC"]]
    inactive: bool

class UpdatedInformationData(BaseModel):
    any_updates: bool
    conferences: list[Conference]

def import_conference(conference: dict) -> Conference:
    conference = copy.deepcopy(conference)
    conference["start"] = str(conference["start"])
    conference["end"] = str(conference["end"])
    conference["note"] = conference.get("note", "")
    conference["inactive"] = conference.get("inactive", False)
    try:
        conference = Conference(**conference)
    except ValidationError as e:
        print("Validation error!")
        print(e)
        print(conference)
        raise e
    return conference

def load_conferences(string: str) -> list[list[Conference]]:
    conferences = yaml.safe_load(string)
    conferences = [ [ import_conference(cycle) for cycle in conference ] for conference in conferences ]
    return conferences

# def dump_conferences(conferences: list[list[Conference]]) -> str:
#     conferences.sort(key=lambda conf: (conf[-1].inactive, conf[-1].deadline, conf[-1].id))
#     return yaml.dump([ [ cycle.__dict__ for cycle in conference ] for conference in conferences ], sort_keys=False)

def load_conference(string: str) -> list[Conference]:
    return [ import_conference(cycle) for cycle in yaml.safe_load(string) ]

def dump_conference(conference: list[Conference]) -> str:
    return yaml.dump([ cycle.__dict__ for cycle in conference ], sort_keys=False)

def main(
    conferences: list[str] = typer.Argument(None),
    training_data_collect: bool = typer.Option(
        False,
        "--training-data-collect",
        help="If set, save model interaction traces for training",
    ),
    training_data_dir: str = typer.Option(
        "chatgpt-updater-training",
        "--training-data-dir",
        help="Directory to store training traces when collection is enabled",
    ),
    refresh: bool = typer.Option(
        False,
        "--refresh",
        help="If set, treat provided conference info as unreliable and re-verify",
    ),
    model: str = typer.Option(
        "gpt-5.1",
        "--model",
        help="OpenAI model to use for completions",
    ),
    api_key_openai: Optional[str] = typer.Option(
        None,
        "--api-key-openai",
        envvar="API_KEY_OPENAI",
        help="OpenAI API key. If omitted, reads from API_KEY_OPENAI env var.",
    ),
    api_key_serper: Optional[str] = typer.Option(
        None,
        "--api-key-serper",
        envvar="API_KEY_SERPER",
        help="Serper.dev API key. If omitted, reads from API_KEY_SERPER env var.",
    ),
    hint: Optional[str] = typer.Option(
        None,
        "--hint",
        help="Optional hint to pass to the LLM to guide the update process",
    ),
) -> None:
    conference_files = []
    if conferences and len(conferences) > 0:
        conference_files = [ f"{filename}.yml" for filename in conferences ]
    else:
        conference_files = list(os.listdir("_data/conferences_raw"))

    for conference_file in sorted(conference_files):
        print("###", conference_file)
        assert(conference_file.endswith(".yml"))

        conference = load_conference(open(os.path.join("_data/conferences_raw", conference_file), "r").read())
        print("BEFORE:", conference)

        if conference[0].inactive:
            print("INACTIVE, SKIPPING!")
            print()
            continue

        messages = [
            {
                "role": "system",
                "content": PROMPT,
            },
            {
                "role": "system",
                "content": str(load_conferences(EXAMPLES))
            },
            {
                "role": "user",
                "content": str(conference)
            }
        ]

        if refresh:
            messages.append({
                "role": "system",
                "content": PROMPT_REFRESH,
            })

        if hint:
            messages.append({
                "role": "system",
                "content": f"Hint: {hint}",
            })

        client = OpenAI(api_key=api_key_openai)

        while True:
            completion = client.beta.chat.completions.parse(
                model=model,
                tools=tools,
                messages=messages,
                response_format=UpdatedInformationData,
            )

            choice = completion.choices[0]

            if choice.finish_reason == "tool_calls":
                messages.append(choice.message)

                for tool_call in choice.message.tool_calls:
                    call_fn = tool_call.function.name
                    call_args = tool_call.function.parsed_arguments
                    ret = None

                    print(">>>", call_fn, call_args)

                    if call_fn == "callback_search":
                        ret = callback_search(serper_api_key=api_key_serper, **call_args)
                    elif call_fn == "callback_browse_html":
                        ret = callback_browse_html(**call_args)
                    elif call_fn == "callback_browse_text":
                        ret = callback_browse_text(**call_args)
                    else:
                        raise Exception("Unknown function!")

                    # print("<<<", ret)

                    messages.append({"role": "tool", "content": json.dumps(ret), "tool_call_id": tool_call.id})

            elif choice.finish_reason == "stop":
                # print("DONE:", choice.message.parsed)

                if choice.message.parsed.any_updates:
                    conference = choice.message.parsed.conferences
                    print("AFTER:", conference)
                    open(os.path.join("_data/conferences_raw", conference_file), "w").write(dump_conference(conference))

                else:
                    print("NO UPDATE!")

                if training_data_collect:
                    messages.append(choice.message)
                    os.makedirs(training_data_dir, exist_ok=True)
                    assert(conference_file.endswith(".yml"))
                    tmp_confid = conference_file[:-len(".yml")]
                    tmp_runid = time.strftime("%Y%m%d-%H%M%S", time.localtime())
                    tmp_updated = "updated" if choice.message.parsed.any_updates else "noupdate"
                    training_data = {
                        "messages": [ m.model_dump() if isinstance(m, BaseModel) else m for m in messages ],
                        "tools": tools,
                        "parallel_tool_calls": True,
                    }
                    open(os.path.join(training_data_dir, f"{tmp_confid}-{tmp_runid}-{tmp_updated}.json"), "w").write(json.dumps(training_data, indent=2))

                break

            else:
                print("ERROR:", choice)
                break

        print()

if __name__ == "__main__":
    typer.run(main)
