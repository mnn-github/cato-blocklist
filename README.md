# Cato HaGeZi Blocklist

Automatically downloads, validates, normalizes, and publishes the **HaGeZi Multi PRO DNS blocklist** in a format suitable for use with a **Cato Networks FQDN Container**.

The project uses **GitHub Actions** to update the blocklist automatically once per day. Cato can then periodically synchronize the generated list from GitHub.

## Overview

This project provides a simple way to use the [HaGeZi DNS Blocklists](https://github.com/hagezi/dns-blocklists) with Cato Networks.

The primary goal is to provide network-wide blocking of:

* Web advertising
* Mobile and Android application advertising
* Tracking domains
* Analytics and telemetry
* Other unwanted domains included in HaGeZi Multi PRO

Cato Networks continues to provide the primary security controls for malicious domains and other threats. HaGeZi provides an additional DNS/domain-based privacy and advertising layer.

### How It Works

```text
HaGeZi Multi PRO
       |
       | Download daily
       v
GitHub Actions
       |
       | normalize.py
       |
       +-- Download source
       +-- Validate domains
       +-- Remove invalid entries
       +-- Deduplicate
       +-- Sort
       +-- Perform sanity checks
       |
       v
output/hagezi-pro.txt
       |
       | GitHub Raw URL
       v
Cato FQDN Container
       |
       v
Cato Internet Firewall
       |
       v
     BLOCK
```

No server, Pi-hole instance, cron server, or other local infrastructure is required.

## Repository Structure

```text
cato-hagezi-blocklist/
|
+-- .github/
|   +-- workflows/
|       +-- update-blocklist.yml
|
+-- scripts/
|   +-- normalize.py
|
+-- output/
|   +-- hagezi-pro.txt
|
+-- README.md
```

### `scripts/normalize.py`

Downloads and processes the current HaGeZi Multi PRO list.

The script:

* Downloads the current HaGeZi source
* Removes comments and blank entries
* Normalizes domains to lowercase
* Removes wildcard notation where necessary
* Validates FQDN syntax
* Rejects IP addresses
* Removes duplicate domains
* Sorts the resulting list
* Performs sanity checks before publishing
* Preserves the previous list if processing fails

### `.github/workflows/update-blocklist.yml`

GitHub Actions workflow responsible for running the update automatically.

The workflow:

1. Starts a GitHub-hosted Linux runner.
2. Checks out this repository.
3. Installs Python.
4. Runs `scripts/normalize.py`.
5. Detects whether the generated blocklist changed.
6. Commits and pushes the new list when necessary.

The workflow can also be started manually from the **Actions** tab.

### `output/hagezi-pro.txt`

The generated Cato-compatible blocklist.

The file contains one FQDN per line:

```text
ads.example.com
analytics.example.com
telemetry.example.net
tracker.example.org
```

This file should not normally be edited manually.

## Source Blocklist

The project uses **HaGeZi Multi PRO**.

Source project:

https://github.com/hagezi/dns-blocklists

The PRO tier was selected as a balance between aggressive advertising/tracker blocking and minimizing disruption to legitimate applications.

The project uses HaGeZi's domains-oriented distribution rather than hosts-file formats such as:

```text
0.0.0.0 ads.example.com
0.0.0.0 tracker.example.com
```

Cato FQDN Containers expect domain values rather than hosts-file mappings.

## Automatic Updates

GitHub Actions runs the update workflow once per day.

The workflow can also be manually executed from:

**Repository → Actions → Update HaGeZi Cato Blocklist → Run workflow**

A successful update should contain steps similar to:

```text
Checkout repository
        |
        v
Set up Python
        |
        v
Download and normalize HaGeZi
        |
        v
Commit updated blocklist
```

If HaGeZi has not changed since the previous run, no new commit is created.

## Safety Checks

The normalizer deliberately performs validation before replacing the existing blocklist.

For example, if the previous list contains approximately:

```text
220,000 domains
```

and a failed download or upstream problem unexpectedly produces:

```text
500 domains
```

the update is rejected.

The existing known-good blocklist remains in the repository.

The script also enforces a minimum expected number of domains and rejects a new list if it is dramatically smaller than the previous version.

This prevents an upstream error, malformed download, or parsing problem from automatically replacing the working Cato blocklist.

## Configuring Cato Networks

After the first successful GitHub Action run, locate:

```text
output/hagezi-pro.txt
```

Click **Raw** in GitHub to obtain the raw file URL.

It will resemble:

```text
https://raw.githubusercontent.com/<USERNAME>/<REPOSITORY>/main/output/hagezi-pro.txt
```

Create an **FQDN Container** in the Cato Management Application and configure it to synchronize from this URL.

Example configuration:

```text
Name:
HaGeZi Multi PRO

Container Type:
FQDN

Source:
Sync file from URL

URL:
https://raw.githubusercontent.com/<USERNAME>/<REPOSITORY>/main/output/hagezi-pro.txt
```

Configure the desired Cato synchronization interval.

GitHub and Cato do not need to synchronize at exactly the same time. For example:

```text
03:17   GitHub Action starts

03:18   New blocklist published

04:00   Cato retrieves blocklist

04:00+  Updated domains become available
        to the Cato policy
```

## Internet Firewall Policy

The FQDN Container can then be referenced by a Cato Internet Firewall rule with a **Block** action.

A simple policy structure might be:

```text
1. HaGeZi Exceptions        ALLOW
2. HaGeZi Multi PRO         BLOCK
3. Remaining Internet Firewall policy...
```

Keeping an explicit exception rule above the block rule makes it easy to restore access if a legitimate application depends on a domain contained in the blocklist.

## False Positives

DNS/domain blocklists can occasionally interfere with legitimate applications.

If an application stops functioning correctly after enabling the list:

1. Identify the blocked FQDN in Cato events.
2. Verify that the domain is required by the application.
3. Add the domain to an appropriate Cato allow/exception rule.
4. Keep the exception above the HaGeZi block rule.

Avoid modifying `hagezi-pro.txt` manually because the next automated update will regenerate the file.

## Manual Updates

The workflow supports manual execution.

Navigate to:

**GitHub → Repository → Actions → Update HaGeZi Cato Blocklist**

Select:

**Run workflow**

This is useful when testing changes to `normalize.py` or when an immediate refresh is desired.

## Monitoring Updates

Every successful blocklist change creates a Git commit.

Git history therefore provides an audit trail showing when the generated blocklist changed.

If an update fails, inspect:

**Repository → Actions → Update HaGeZi Cato Blocklist**

The failed workflow contains the output from `normalize.py`, including validation errors.

## Requirements

No dedicated infrastructure is required.

The project uses:

* GitHub
* GitHub Actions
* Python 3
* HaGeZi DNS Blocklists
* Cato Networks FQDN Containers

The Python script uses only the Python standard library and does not require additional packages or `pip install`.

## Security Considerations

This project intentionally places a validation layer between the upstream blocklist and Cato.

The data flow is:

```text
Third-party source
       |
       v
Download
       |
       v
Validate
       |
       v
Normalize
       |
       v
Sanity check
       |
       v
Publish
       |
       v
Cato
```

An upstream list should not be treated as trusted input simply because it is automatically downloaded.

The normalizer therefore validates entries and performs basic integrity checks before publishing a new version.

## Disclaimer

This is an independent integration project and is not an official HaGeZi or Cato Networks product.

Use of third-party blocklists can cause legitimate domains or applications to be blocked. Review your environment and firewall events when troubleshooting application connectivity.

HaGeZi DNS Blocklists are maintained by their respective project contributors. Refer to the HaGeZi project for current licensing, list descriptions, and upstream documentation.

## Credits

* [HaGeZi DNS Blocklists](https://github.com/hagezi/dns-blocklists)
* [Cato Networks](https://www.catonetworks.com/)
* [GitHub Actions](https://github.com/features/actions)
