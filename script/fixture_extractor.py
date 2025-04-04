import requests
from bs4 import BeautifulSoup
from datetime import timedelta
import json
import os
import re
import time
import random
from daterangeparser import parse as parse_date
import dateparser


def parse_date_range(date_str):
    if not date_str:
        return None, None

    try:
        # Clean up the date string
        date_str = date_str.replace(",", "").strip()

        # Check if it's a single date (no hyphen)
        if "-" not in date_str:
            single_date = dateparser.parse(date_str)
            if single_date:
                return single_date.date(), single_date.date()
            return None, None

        # Parse the date range
        start_date, end_date = parse_date(date_str)
        return start_date.date(), end_date.date()
    except Exception as e:
        print(f"Error parsing date range '{date_str}': {e}")
        return None, None


def parse_start_time_gmt(status_text):
    match = re.search(
        r"\((?:\d{1,2}:\d{2})\s+local\s+\|\s+(\d{1,2}:\d{2})\s+GMT\)", status_text
    )
    if match:
        t = dateparser.parse(match.group(1) + " GMT")
        return t.time() if t else None
    return None


def extract_venue(match_title):
    if not match_title:
        return None
    parts = match_title.split(" at ")
    return parts[1].strip() if len(parts) == 2 else None


def parse_fixtures(url, competition):
    fixtures = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3.1 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
    }

    # Add a random delay between requests to be more human-like
    time.sleep(random.uniform(2, 5))

    session = requests.Session()
    response = session.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    match_sections = soup.find_all("section", class_="default-match-block")

    for match in match_sections:
        try:
            date_span = match.find("div", class_="match-info").find(
                "span", class_="bold"
            )
            date_text = date_span.get_text(strip=True) if date_span else None
            start_date, end_date = parse_date_range(date_text)

            match_no_anchor = match.find("div", class_="match-info").find("a")
            match_title = (
                match_no_anchor.get_text(strip=True) if match_no_anchor else None
            )
            match_url = match_no_anchor["href"] if match_no_anchor else None
            venue = extract_venue(match_title)

            team1 = match.find("div", class_="innings-info-1").get_text(strip=True)
            team2 = match.find("div", class_="innings-info-2").get_text(strip=True)

            status_div = match.find("div", class_="match-status")
            status_text = status_div.get_text(strip=True) if status_div else ""
            start_time_gmt = parse_start_time_gmt(status_text)

            fixtures.append(
                {
                    "competition": competition,
                    "match_url": match_url,
                    "team1": team1,
                    "team2": team2,
                    "start_date": start_date,
                    "end_date": end_date,
                    "start_time_gmt": start_time_gmt,
                    "venue": venue,
                }
            )
        except Exception as e:
            print(f"Error parsing a fixture from {url}: {e}")

    return fixtures


def group_fixtures_by_day(fixtures):
    grouped = {}
    for fixture in fixtures:
        start = fixture["start_date"]
        end = fixture["end_date"]
        
        # Skip fixtures with missing dates
        if start is None or end is None:
            print(f"Skipping fixture with missing dates: {fixture.get('team1', 'Unknown')} vs {fixture.get('team2', 'Unknown')}")
            continue
            
        current = start
        while current <= end:
            key = current.isoformat()
            grouped.setdefault(key, []).append(fixture)
            current += timedelta(days=1)
    return grouped


def write_fixtures_to_json(grouped_fixtures, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for day, matches in grouped_fixtures.items():
        path = os.path.join(output_dir, f"{day}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(matches, f, indent=2, default=str)
        print(f"Wrote {len(matches)} matches to {path}")


if __name__ == "__main__":
    # 👇 Add more (url, competition) pairs here if needed
    inputs = [
        (
            "https://www.espncricinfo.com/ci/engine/match/index/series.html?series=16856",
            "County Championship Division One",
        ),
        (
            "https://www.espncricinfo.com/ci/engine/match/index/series.html?series=16857",
            "County Championship Division Two",
        ),
        (
            "https://www.espncricinfo.com/ci/engine/match/index/series.html?series=16858",
            "One-Day Cup",
        ),
        (
            "https://www.espncricinfo.com/ci/engine/match/index/series.html?series=16846",
            "T20 Blast",
        ),
    ]

    all_fixtures = []
    for url, competition in inputs:
        print(f"Parsing {competition} from {url}")
        all_fixtures.extend(parse_fixtures(url, competition))

    grouped = group_fixtures_by_day(all_fixtures)
    write_fixtures_to_json(grouped, output_dir="public/data/fixtures")
