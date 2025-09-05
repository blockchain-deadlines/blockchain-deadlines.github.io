#! /usr/bin/env python3

import os
import requests
import json
import yaml
import copy
import time
import ssl
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError
from typing import Literal, Optional
from openai import OpenAI
import typer


PROMPT = """
# Overall Goal

Find the submission deadline information for the latest edition (for which a call-for-papers with submission deadline information is available online) of the conference (or other academic venue) specified by the user.
If the user-provided information is for year X, then try to find the information for year X+1, etc. If no more up-to-date information is available, then return no update.


# Information Sources

Consider only information from authoritative sources. Examples for authoritative sources are the conference's website, the conference organizer, the publisher of the conference proceedings, or reputable professional organizations (IACR, IEEE, ACM, etc.).
Do not consider information from third parties. Examples of third parties are conference deadline aggregators (e.g., mpc-deadlines.github.io, wikicfp.com, sslab.skku.edu, aconf.org, etc.).
If you find the information on a third-party website, make every effort to locate the official source. Use that official source for the `link` field and to population the other fields. If you cannot verify information on third-party websites through official sources, then better return no update.
To find information, search for the conference edition's website, or make educated guesses as to what the website URL could be, based on the URLs of previous years.


# Data Format

If there are multiple submission cycles for the conference, produce a separate conference object for each submission cycle.
If there are multiple deadlines mentioned for a particular submission cycle (e.g., an abstract registration/submission deadline and a full paper submission deadline), choose the earliest deadline for the `deadline` field, and mention in the `note` field what the deadline used in `deadline` is for, and mention in the `note` field all other deadlines of that cycle.
Include in `note` also information about the author notification date (without time and timezone information).
Do not include information in `note` any other than the aforementioned information.
In particular, do not include in `note` any deadline information regarding early-rejection, rebuttal, camera-ready, workshop/tutorial proposals, or conference registration for attendance.
Do not include in `note` information about whether the deadline is firm.
Pay attention to timezone information and specify them in `note` as well. Do proper conversion from AM/PM to 24h format. Deadlines in 'anywhere on earth' = 'AoE' should be flagged with `timezone` `Etc/GMT+12`.
For `link`, provide the URL that contains the official source of the submission deadline information.
Subject areas in `sub` are `BC` (blockchain), `CR` (cryptography), `DS` (distributed systems), `SEC` (security), and `EC` (economics/incentives).


# Tools

Prefer text content over HTML content, when possible, because text content is cheaper to retrieve than HTML content.


# Examples

I will provide you with example information for a few conferences, so that you can understand the desired data format.
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
    note: ''
    place: Hotel Shigira Mirage, Miyakojima, Japan
    date: 14–18 April 2025
    start: 2024-04-14
    end: 2024-04-18
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
"""

PROMPT_REFRESH = """
Refresh requested: Treat the user-provided deadline information as potentially unreliable. Re-verify all details of the provided information from official sources before returning it as an update or indicating that no update is needed. You may assume that the `full_title` and `year` fields are correct and should not be changed.
"""


def callback_search(query: str, serper_api_key: str) -> list[tuple[str, str, str, str, str]]:
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

    returns = []

    if "answerBox" in results:
        returns.append((results["answerBox"]["title"], results["answerBox"]["link"], "HIGHLIGHTED-RESULT", results["answerBox"]["snippet"], results["answerBox"].get("snippetHighlighted", "")))

    for result in results["organic"]:
        returns.append((result["title"], result["link"], "REGULAR-RESULT", result["snippet"], ""))
        if "sitelinks" in result:
            for sitelink in result["sitelinks"]:
                returns.append((sitelink["title"], sitelink["link"], "GIVEN-AS-ADDITIONAL-SITELINK-TO-REGULAR-RESULT", "", ""))
    
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
    return _guard_max_return_length(text)

def callback_browse_text(url: str) -> list[str]:
    html = _retrieve_url(url)
    soup = BeautifulSoup(html, "html.parser")
    text = list(soup.stripped_strings)
    return _guard_max_return_length(text)

tools = [
    {
        "type": "function",
        "function": {
            "name": "callback_search",
            "description": "Search the web for information. Call this and provide a search query whenever you need to search the web for information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to search the web for information.",
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
            "description": "Get HTML content of a website via the http or https URL. Call this and provide a URL whenever you want to retrieve the HTML content of a web page. This function provides more detailed input than callback_browse_text, but is also more expensive, so use it only when necessary.",
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
            "description": "Get text content of a website via the http or https URL. Call this and provide a URL whenever you want to retrieve the text content of a web page. This function provides less detailed input than callback_browse_html, but is also cheaper, so use it when possible.",
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
        "gpt-5",
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
                    tmp_runid = str(int(time.time()))
                    tmp_updated = "updated" if choice.message.parsed.any_updates else "noupdate"
                    open(os.path.join(training_data_dir, f"{tmp_confid}-run{tmp_runid}-{tmp_updated}.json"), "w").write(json.dumps([ m.model_dump() if isinstance(m, BaseModel) else m for m in messages ], indent=2))

                break

            else:
                print("ERROR:", choice)
                break

        print()

if __name__ == "__main__":
    typer.run(main)
