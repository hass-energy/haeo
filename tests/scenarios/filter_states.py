#!/usr/bin/env python3
# ruff: noqa: T201 Allow print statements for the script

"""HAEO Scenario States Filter Script.

This script helps filter Home Assistant states for scenario testing.
It takes a list of sensor patterns to keep and filters the states accordingly.
"""

import argparse
import getpass
import json
from pathlib import Path
import re
import sys
from typing import Any, cast
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urljoin


def get_home_assistant_token() -> str:
    """Prompt user for Home Assistant long-lived access token."""
    print("Please enter your Home Assistant long-lived access token:")
    token = getpass.getpass("Token: ")
    if not token:
        print("Error: Token cannot be empty")
        sys.exit(1)
    return token


def fetch_home_assistant_states(url: str, token: str) -> list[dict[str, Any]]:
    """Fetch states from Home Assistant API."""
    try:
        # Construct the full URL for the states endpoint
        states_url = urljoin(url.rstrip("/") + "/", "api/states")

        # Create request with authorization header
        req = urllib_request.Request(states_url)  # noqa: S310
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")

        # Make the request
        with urllib_request.urlopen(req) as response:  # noqa: S310
            raw = json.loads(response.read().decode("utf-8"))

        if not isinstance(raw, list):
            msg = "Home Assistant API returned unexpected payload"
            raise TypeError(msg)

        state_list: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                msg = "Encountered non-object state entry"
                raise TypeError(msg)
            state_list.append(cast("dict[str, Any]", item))

        return state_list

    except urllib_error.HTTPError as e:
        if e.code == 401:
            print("Error: Invalid token or authentication failed")
        elif e.code == 404:
            print("Error: Home Assistant URL not found. Make sure you're using the correct URL.")
        else:
            print(f"Error: HTTP {e.code} - {e.reason}")
        sys.exit(1)
    except urllib_error.URLError as e:
        print(f"Error: Could not connect to Home Assistant at {url}")
        print(f"Details: {e.reason}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON response from Home Assistant")
        sys.exit(1)


def main() -> None:
    """Filter Home Assistant states for HAEO scenario testing."""
    parser = argparse.ArgumentParser(
        description="Filter Home Assistant states for HAEO scenario testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
          Examples:
            %(prog)s input.json -o output.json sensor.battery sensor.solar sensor.grid
            %(prog)s full_states.json --output filtered.json --patterns sensor.battery_soc sensor.import_price
            %(prog)s states.json --output output.json --patterns-from-file sensors.txt
            %(prog)s http://homeassistant.local:8123 -o output.json sensor.battery sensor.solar
                """,
    )

    parser.add_argument("input_source", help="Input file path or Home Assistant URL")

    parser.add_argument("--output", "-o", help="Output JSON file for filtered states")
    parser.add_argument("--patterns-from-file", "-p", help="File containing sensor patterns separated by whitespace")
    parser.add_argument("patterns", nargs="*", help="Sensor patterns to keep (e.g., sensor.battery, sensor.solar)")

    args = parser.parse_args()

    patterns = []
    if args.patterns_from_file:
        with Path.open(args.patterns_from_file) as f:
            # Split on any whitespace
            patterns = re.split(r"\s+", f.read().strip())
    patterns.extend(args.patterns)

    if not patterns:
        print("Error: No patterns specified. Use --patterns-from-file or provide patterns as arguments.")
        return

    print(f"Filtering states using {len(patterns)} patterns")

    # Auto-detect if input_source is a URL or file path
    if args.input_source.startswith(("http://", "https://")):
        # Fetch from Home Assistant API
        token = get_home_assistant_token()
        print(f"Fetching states from Home Assistant at {args.input_source}...")
        data = fetch_home_assistant_states(args.input_source, token)
        source_name = args.input_source
    else:
        # Load from file
        input_path = Path(args.input_source)
        if not input_path.exists():
            print(f"Error: Input file '{args.input_source}' does not exist")
            return
        with input_path.open() as f:
            data = json.load(f)
        source_name = args.input_source

    input_count = len(data)
    print(f"Loaded {input_count} states from {source_name}")

    filtered = sorted([e for e in data if e["entity_id"] in patterns], key=lambda x: x["entity_id"])

    output_count = len(filtered)
    print(f"Filtered to {output_count} states ({output_count / input_count * 100:.1f}% of original)")

    with Path.open(args.output, "w") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)

    print(f"Saved filtered states to {args.output}")


if __name__ == "__main__":
    main()
