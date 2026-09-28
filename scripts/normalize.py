#!/usr/bin/env python3

from pathlib import Path
import ipaddress
import re
import sys
import urllib.request


SOURCE_URL = (
    "https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@latest/"
    "wildcard/pro-onlydomains.txt"
)

OUTPUT_FILE = Path("output/hagezi-pro.txt")

# Safety settings
MINIMUM_DOMAINS = 100_000
MINIMUM_SIZE_RATIO = 0.70
DOWNLOAD_TIMEOUT = 60

USER_AGENT = "Cato-HaGeZi-Updater/1.0"


DOMAIN_LABEL = re.compile(
    r"^(?!-)[a-z0-9-]{1,63}(?<!-)$",
    re.IGNORECASE,
)


def valid_domain(domain: str) -> bool:
    """Validate that a string looks like an FQDN."""

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

    if len(labels) < 2:
        return False

    return all(DOMAIN_LABEL.match(label) for label in labels)


def download_source() -> str:
    """Download the current HaGeZi PRO domains-only list."""

    print(f"Downloading:\n  {SOURCE_URL}")

    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": USER_AGENT},
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
            f"Unable to download HaGeZi list: {exc}"
        ) from exc

    if not data:
        raise RuntimeError("Downloaded list is empty.")

    print(f"Downloaded {len(data):,} bytes.")

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            "Downloaded list is not valid UTF-8."
        ) from exc


def normalize(text: str) -> set[str]:
    """Normalize and validate source domains."""

    domains = set()
    invalid = 0

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        # Remove inline comments.
        if "#" in line:
            line = line.split("#", 1)[0].strip()

        line = line.lower()

        # Defensive handling in case wildcard notation appears.
        if line.startswith("*."):
            line = line[2:]

        # Remove leading/trailing DNS notation.
        line = line.lstrip(".")
        line = line.rstrip(".")

        if not line:
            continue

        if valid_domain(line):
            domains.add(line)
        else:
            invalid += 1

    print()
    print("Normalization:")
    print(f"  Valid unique domains : {len(domains):,}")
    print(f"  Invalid/skipped      : {invalid:,}")

    return domains


def read_existing_count() -> int:
    """Count domains in the currently published list."""

    if not OUTPUT_FILE.exists():
        return 0

    with OUTPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return sum(
            1
            for line in file
            if line.strip()
        )


def validate_new_list(domains: set[str]) -> None:
    """Protect against publishing a broken or incomplete feed."""

    new_count = len(domains)

    if new_count < MINIMUM_DOMAINS:
        raise RuntimeError(
            f"Only {new_count:,} valid domains were found. "
            f"Expected at least {MINIMUM_DOMAINS:,}. "
            "Refusing to replace the existing list."
        )

    old_count = read_existing_count()

    if old_count == 0:
        print()
        print("No existing list found; skipping size comparison.")
        return

    ratio = new_count / old_count
    percent_change = (
        (new_count - old_count) / old_count
    ) * 100

    print()
    print("Existing-list comparison:")
    print(f"  Previous : {old_count:,}")
    print(f"  New      : {new_count:,}")
    print(f"  Change   : {percent_change:+.2f}%")

    if ratio < MINIMUM_SIZE_RATIO:
        raise RuntimeError(
            "New list is more than 30% smaller than the "
            "previous list. Refusing to publish it."
        )


def write_output(domains: set[str]) -> None:
    """Write the final Cato-compatible domain list."""

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = OUTPUT_FILE.with_suffix(".tmp")

    try:
        with temp_file.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:

            for domain in sorted(domains):
                file.write(domain + "\n")

        # Replace only after the new file is complete.
        temp_file.replace(OUTPUT_FILE)

    except Exception:
        temp_file.unlink(missing_ok=True)
        raise

    print()
    print(f"Published {len(domains):,} domains to:")
    print(f"  {OUTPUT_FILE}")


def main() -> int:

    print("=" * 60)
    print("HaGeZi Multi PRO -> Cato FQDN Normalizer")
    print("=" * 60)

    try:
        source = download_source()
        domains = normalize(source)
        validate_new_list(domains)
        write_output(domains)

    except Exception as exc:

        print()
        print("ERROR:")
        print(exc)
        print()
        print("Existing blocklist was not replaced.")

        return 1

    print()
    print("SUCCESS")

    return 0


if __name__ == "__main__":
    sys.exit(main())
