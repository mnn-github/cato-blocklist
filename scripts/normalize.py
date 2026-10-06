#!/usr/bin/env python3

"""
Cato FQDN Blocklist Normalizer

Processes two upstream DNS/domain blocklists:

1. HaGeZi Multi PRO
2. StevenBlack Unified hosts (adware + malware)

Outputs:

    output/hagezi-pro.txt
    output/stevenblack-unified.txt

Each output file contains exactly one normalized FQDN per line.

The script performs:
- upstream downloads
- format-specific parsing
- FQDN validation
- lowercase normalization
- deduplication
- sorting
- minimum-size checks
- comparison against the previous output
- atomic replacement of output files

No third-party Python packages are required.
"""

from pathlib import Path
import ipaddress
import re
import sys
import urllib.request


# ---------------------------------------------------------------------------
# Global configuration
# ---------------------------------------------------------------------------

DOWNLOAD_TIMEOUT = 60
USER_AGENT = "Cato-Blocklist-Updater/2.0"

OUTPUT_DIRECTORY = Path("output")

# Reject a new list if it falls below 70% of its previous size.
#
# This protects against upstream/download/parser failures.
MINIMUM_SIZE_RATIO = 0.70


# ---------------------------------------------------------------------------
# Feed definitions
# ---------------------------------------------------------------------------

FEEDS = [
    {
        "name": "HaGeZi Multi PRO",

        # HaGeZi Wildcard Domains / domains-only format.
        "url": (
            "https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@latest/"
            "wildcard/pro-onlydomains.txt"
        ),

        "output": OUTPUT_DIRECTORY / "hagezi-pro.txt",

        # HaGeZi PRO normally contains well over 100,000 domains.
        "minimum_domains": 100_000,

        "format": "domains",
    },

    {
        "name": "StevenBlack Unified",

        # StevenBlack's official Unified:
        # adware + malware hosts file.
        "url": (
            "https://raw.githubusercontent.com/"
            "StevenBlack/hosts/master/hosts"
        ),

        "output": OUTPUT_DIRECTORY / "stevenblack-unified.txt",

        # StevenBlack Unified is currently around 70k domains.
        # Use a deliberately conservative floor.
        "minimum_domains": 40_000,

        "format": "hosts",
    },
]


# ---------------------------------------------------------------------------
# Domain validation
# ---------------------------------------------------------------------------

DOMAIN_LABEL = re.compile(
    r"^(?!-)[a-z0-9-]{1,63}(?<!-)$",
    re.IGNORECASE,
)


def valid_domain(domain: str) -> bool:
    """
    Return True if the supplied value looks like a valid Internet FQDN.

    The function rejects:
    - empty values
    - IP addresses
    - single-label hostnames
    - over-length domains
    - labels containing invalid characters
    """

    if not domain:
        return False

    if len(domain) > 253:
        return False

    # Reject IP addresses.
    try:
        ipaddress.ip_address(domain)
        return False
    except ValueError:
        pass

    labels = domain.split(".")

    # Require an actual FQDN.
    if len(labels) < 2:
        return False

    return all(
        DOMAIN_LABEL.match(label)
        for label in labels
    )


def normalize_domain(domain: str) -> str:
    """
    Normalize common domain representations.

    Examples:

        *.example.com  -> example.com
        .example.com   -> example.com
        example.com.   -> example.com
        EXAMPLE.COM    -> example.com
    """

    domain = domain.strip().lower()

    if domain.startswith("*."):
        domain = domain[2:]

    domain = domain.lstrip(".")
    domain = domain.rstrip(".")

    return domain


# ---------------------------------------------------------------------------
# Download handling
# ---------------------------------------------------------------------------

def download_source(feed: dict) -> str:
    """
    Download an upstream blocklist and return it as UTF-8 text.
    """

    print()
    print(f"Downloading {feed['name']}:")
    print(f"  {feed['url']}")

    request = urllib.request.Request(
        feed["url"],
        headers={
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=DOWNLOAD_TIMEOUT,
        ) as response:

            if response.status != 200:
                raise RuntimeError(
                    f"Unexpected HTTP status: {response.status}"
                )

            data = response.read()

    except Exception as exc:
        raise RuntimeError(
            f"Unable to download {feed['name']}: {exc}"
        ) from exc

    if not data:
        raise RuntimeError(
            f"{feed['name']} returned an empty file."
        )

    print(f"  Downloaded {len(data):,} bytes")

    try:
        return data.decode("utf-8")

    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"{feed['name']} is not valid UTF-8."
        ) from exc


# ---------------------------------------------------------------------------
# HaGeZi parser
# ---------------------------------------------------------------------------

def parse_domains_format(text: str) -> set[str]:
    """
    Parse a domains-only blocklist such as HaGeZi Wildcard Domains.

    Expected examples:

        ads.example.com
        tracker.example.net
        *.telemetry.example.org
    """

    domains: set[str] = set()

    invalid = 0
    comments = 0
    blank = 0

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            blank += 1
            continue

        if line.startswith("#"):
            comments += 1
            continue

        # Strip inline comments.
        if "#" in line:
            line = line.split("#", 1)[0].strip()

        if not line:
            continue

        domain = normalize_domain(line)

        if valid_domain(domain):
            domains.add(domain)
        else:
            invalid += 1

    print("  Parser statistics:")
    print(f"    Valid unique domains : {len(domains):,}")
    print(f"    Invalid/skipped      : {invalid:,}")
    print(f"    Comment lines        : {comments:,}")
    print(f"    Blank lines          : {blank:,}")

    return domains


# ---------------------------------------------------------------------------
# StevenBlack parser
# ---------------------------------------------------------------------------

def parse_hosts_format(text: str) -> set[str]:
    """
    Parse traditional hosts-file format.

    StevenBlack contains entries similar to:

        0.0.0.0 ads.example.com
        0.0.0.0 tracker.example.net

    The sinkhole IP address is discarded.

    Only the hostname is written to the Cato FQDN output.
    """

    domains: set[str] = set()

    invalid = 0
    comments = 0
    blank = 0
    localhost = 0

    # Common local/system names that should never be placed
    # into the Cato blocklist.
    excluded_hostnames = {
        "localhost",
        "localhost.localdomain",
        "local",
        "broadcasthost",
        "ip6-localhost",
        "ip6-loopback",
        "ip6-localnet",
        "ip6-mcastprefix",
        "ip6-allnodes",
        "ip6-allrouters",
    }

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            blank += 1
            continue

        if line.startswith("#"):
            comments += 1
            continue

        # Remove inline comments.
        #
        # Example:
        #
        # 0.0.0.0 ads.example.com # advertising
        #
        if "#" in line:
            line = line.split("#", 1)[0].strip()

        if not line:
            continue

        # Hosts syntax consists of whitespace-separated fields.
        #
        # Example:
        #
        # 0.0.0.0 ads.example.com
        #
        fields = line.split()

        if len(fields) < 2:
            invalid += 1
            continue

        # First field is the sinkhole IP.
        # Remaining fields are hostnames.
        hostnames = fields[1:]

        for hostname in hostnames:

            domain = normalize_domain(hostname)

            if domain in excluded_hostnames:
                localhost += 1
                continue

            if valid_domain(domain):
                domains.add(domain)
            else:
                invalid += 1

    print("  Parser statistics:")
    print(f"    Valid unique domains : {len(domains):,}")
    print(f"    Invalid/skipped      : {invalid:,}")
    print(f"    Localhost/system     : {localhost:,}")
    print(f"    Comment lines        : {comments:,}")
    print(f"    Blank lines          : {blank:,}")

    return domains


# ---------------------------------------------------------------------------
# Parser selection
# ---------------------------------------------------------------------------

def parse_feed(feed: dict, text: str) -> set[str]:
    """
    Select the appropriate parser based on the feed definition.
    """

    if feed["format"] == "domains":
        return parse_domains_format(text)

    if feed["format"] == "hosts":
        return parse_hosts_format(text)

    raise RuntimeError(
        f"Unknown feed format: {feed['format']}"
    )


# ---------------------------------------------------------------------------
# Existing output handling
# ---------------------------------------------------------------------------

def read_existing_count(output_file: Path) -> int:
    """
    Return the number of non-empty entries in the previous output file.

    Returns 0 when the file does not yet exist.
    """

    if not output_file.exists():
        return 0

    try:
        with output_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            return sum(
                1
                for line in file
                if line.strip()
            )

    except OSError as exc:
        raise RuntimeError(
            f"Unable to read existing output file "
            f"{output_file}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Feed safety validation
# ---------------------------------------------------------------------------

def validate_feed(
    feed: dict,
    domains: set[str],
) -> None:
    """
    Validate the new list before replacing the previous one.
    """

    new_count = len(domains)

    minimum_domains = feed["minimum_domains"]
    output_file = feed["output"]

    if new_count < minimum_domains:

        raise RuntimeError(
            f"{feed['name']} produced only "
            f"{new_count:,} valid domains. "
            f"Expected at least {minimum_domains:,}. "
            "Refusing to publish."
        )

    old_count = read_existing_count(output_file)

    if old_count == 0:

        print(
            "  No previous output exists; "
            "skipping size comparison."
        )

        return

    ratio = new_count / old_count

    percent_change = (
        (new_count - old_count)
        / old_count
    ) * 100

    print("  Previous-list comparison:")
    print(f"    Previous : {old_count:,}")
    print(f"    New      : {new_count:,}")
    print(f"    Change   : {percent_change:+.2f}%")

    if ratio < MINIMUM_SIZE_RATIO:

        raise RuntimeError(
            f"{feed['name']} is more than 30% smaller "
            "than the previous version. "
            "Refusing to publish."
        )


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------

def write_output(
    feed: dict,
    domains: set[str],
) -> None:
    """
    Atomically write a normalized feed to its output file.
    """

    output_file = feed["output"]

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = output_file.with_suffix(".tmp")

    try:

        with temp_file.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:

            for domain in sorted(domains):
                file.write(domain + "\n")

        # Replace the previous file only after the complete
        # new version has been written successfully.
        temp_file.replace(output_file)

    except Exception:

        temp_file.unlink(missing_ok=True)
        raise

    print(
        f"  Published {len(domains):,} domains to:"
    )
    print(f"    {output_file}")


# ---------------------------------------------------------------------------
# Process a single feed
# ---------------------------------------------------------------------------

def process_feed(feed: dict) -> None:
    """
    Download, parse, validate, and publish a single feed.
    """

    print()
    print("=" * 70)
    print(feed["name"])
    print("=" * 70)

    source = download_source(feed)

    domains = parse_feed(
        feed,
        source,
    )

    validate_feed(
        feed,
        domains,
    )

    write_output(
        feed,
        domains,
    )

    print(f"  {feed['name']}: SUCCESS")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """
    Process all configured feeds.

    IMPORTANT:

    The script returns failure if ANY feed fails.

    This means GitHub Actions will not reach the commit step when:
    - HaGeZi fails, or
    - StevenBlack fails.

    This prevents publishing a partial update set.
    """

    print("=" * 70)
    print("Cato FQDN Blocklist Updater")
    print("=" * 70)

    try:

        for feed in FEEDS:
            process_feed(feed)

    except Exception as exc:

        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)

        print(exc)

        print()
        print(
            "GitHub commit step will not run."
        )

        return 1

    print()
    print("=" * 70)
    print("ALL FEEDS SUCCESSFUL")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
