Replace your existing `README.md` with the following. This version documents both independent blocklists, the single normalization script, and the single scheduled GitHub Action.

# Cato Blocklist Automation

Automatically downloads, validates, normalizes, and publishes multiple DNS blocklists in a format suitable for **Cato Networks FQDN Containers**.

The project currently processes:

* **HaGeZi Multi PRO** — ads, trackers, telemetry, and related unwanted domains
* **StevenBlack Unified** — adware + malware

Each source is published as a **separate output file** so it can be assigned to its own Cato FQDN Container.

A single **GitHub Actions** workflow updates both lists automatically once per day.

---

## Overview

This project provides network-wide domain blocking without requiring Pi-hole or another locally hosted DNS filtering service.

The primary goals are:

* Block web advertising
* Block advertising used by Android/mobile applications and games
* Block tracking and telemetry domains
* Provide an additional layer of adware/malware domain blocking
* Use Cato Networks as the enforcement point
* Automatically maintain the blocklists
* Require no dedicated server, VM, cron server, or other local infrastructure

Cato Networks remains the primary security platform. These third-party blocklists provide an additional domain-based advertising, privacy, and security layer.

---

# Architecture

```text
                    GitHub Actions
                         |
                         | Daily at 03:17 Eastern
                         |
              +----------+----------+
              |                     |
              v                     v
       HaGeZi Multi PRO      StevenBlack Unified
              |              (adware + malware)
              |                     |
              +----------+----------+
                         |
                         v
                   normalize.py
                         |
              +----------+----------+
              |                     |
              v                     v
      hagezi-pro.txt       stevenblack-unified.txt
              |                     |
              v                     v
       Cato FQDN            Cato FQDN
        Container            Container
              |                     |
              +----------+----------+
                         |
                         v
                 Internet Firewall
                         |
                         v
                       BLOCK
```

GitHub provides the temporary Linux runner used to execute the Python script.

No local Python installation, Pi-hole server, cron server, or dedicated VM is required.

---

# Blocklists

## HaGeZi Multi PRO

Source project:

[https://github.com/hagezi/dns-blocklists](https://github.com/hagezi/dns-blocklists)

This project uses the **Multi PRO Wildcard Domains / Domains Only** feed.

Source:

```text
https://cdn.jsdelivr.net/gh/hagezi/dns-blocklists@latest/wildcard/pro-onlydomains.txt
```

The PRO tier provides a balance between aggressive advertising/tracker blocking and minimizing disruption to legitimate applications.

It is particularly useful for:

* Web advertising
* Tracking
* Analytics
* Telemetry
* Mobile application advertising
* Mobile application tracking

The domains-oriented version is used because it is already close to the format required by a Cato FQDN Container.

---

## StevenBlack Unified

Source project:

[https://github.com/StevenBlack/hosts](https://github.com/StevenBlack/hosts)

This project uses:

**Unified hosts = adware + malware**

Source:

```text
https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
```

StevenBlack uses traditional hosts-file syntax:

```text
0.0.0.0 ads.example.com
0.0.0.0 malware.example.net
```

The IP address:

```text
0.0.0.0
```

is a hosts-file sinkhole address.

It is **not** the actual IP address of the destination and should not be imported into a Cato IP Container.

The normalizer therefore extracts only:

```text
ads.example.com
malware.example.net
```

---

# Why Keep the Lists Separate?

Although there is overlap between HaGeZi and StevenBlack, the generated files intentionally remain separate.

This provides two independent Cato Containers:

```text
HaGeZi Multi PRO
      |
      v
Cato FQDN Container
```

and:

```text
StevenBlack Unified
      |
      v
Cato FQDN Container
```

This provides better:

* Troubleshooting
* Visibility
* Policy control
* Testing
* Rollback capability

If a legitimate domain is blocked, it is easier to determine which source contains the domain.

The lists can also be enabled or disabled independently in Cato.

---

# Repository Structure

```text
cato-blocklist/
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
|   +-- stevenblack-unified.txt
|
+-- README.md
```

The `output` directory and generated files are created automatically by `normalize.py`.

---

# `scripts/normalize.py`

The Python script handles both upstream feeds.

It:

1. Downloads HaGeZi Multi PRO.
2. Parses its domains-only format.
3. Downloads StevenBlack Unified.
4. Parses its hosts-file format.
5. Extracts FQDNs.
6. Normalizes domains to lowercase.
7. Validates FQDN syntax.
8. Rejects IP addresses.
9. Removes local/system hostnames.
10. Removes duplicates.
11. Sorts the output.
12. Performs list-size sanity checks.
13. Compares new lists against previous versions.
14. Atomically replaces known-good output files.

The script uses only the Python standard library.

No:

```text
pip install
```

or:

```text
requirements.txt
```

is required.

---

# Generated Files

## HaGeZi

```text
output/hagezi-pro.txt
```

## StevenBlack

```text
output/stevenblack-unified.txt
```

Both files contain exactly one FQDN per line:

```text
ads.example.com
analytics.example.net
malware.example.org
tracker.example.com
```

They should not contain:

```text
0.0.0.0 ads.example.com
```

or Adblock syntax such as:

```text
||ads.example.com^
```

---

# GitHub Actions

The project uses a single workflow:

```text
.github/workflows/update-blocklist.yml
```

The workflow processes **both blocklists** during the same execution.

The normal workflow is:

```text
GitHub Scheduler
       |
       v
Checkout repository
       |
       v
Configure Python
       |
       v
Run normalize.py
       |
       +---- HaGeZi
       |
       +---- StevenBlack
       |
       v
Validate both lists
       |
       v
Generate output files
       |
       v
Did anything change?
       |
       +---- No ----> Finish
       |
       +---- Yes ---> Commit
                       |
                       v
                      Push
```

---

# Update Schedule

The GitHub Action runs every day at:

```text
03:17 AM Eastern Time
```

The workflow contains:

```yaml
on:
  schedule:
    - cron: "17 3 * * *"
      timezone: "America/New_York"

  workflow_dispatch:
```

Using:

```text
America/New_York
```

allows the schedule to follow Eastern Standard Time and Eastern Daylight Time automatically.

The `workflow_dispatch` trigger also provides a **Run workflow** button for manual testing.

---

# GitHub Permissions

The workflow requires:

```yaml
permissions:
  contents: write
```

This allows the GitHub Actions bot to commit updated output files back to the repository.

---

# GitHub Runner

The workflow uses:

```yaml
runs-on: ubuntu-latest
```

GitHub supplies and maintains the temporary Linux runner.

The repository is checked out using:

```yaml
uses: actions/checkout@v7
```

Python is configured using:

```yaml
uses: actions/setup-python@v7
```

---

# Manual Update

The workflow can be run manually from:

```text
Repository
  -> Actions
  -> Update Cato Blocklists
  -> Run workflow
```

This is useful when:

* Initially configuring the repository
* Testing changes
* Updating `normalize.py`
* Updating the GitHub workflow
* Forcing an immediate refresh

A manual run is identified by:

```text
workflow_dispatch
```

A scheduled run is identified by:

```text
schedule
```

---

# Successful Run

A successful execution should show:

```text
Checkout repository                 PASS
Set up Python                       PASS
Download and normalize blocklists   PASS
Commit updated blocklists           PASS
```

The normalizer should report statistics separately for each feed.

Example:

```text
======================================================================
HaGeZi Multi PRO
======================================================================

Downloading HaGeZi Multi PRO:
  ...

Parser statistics:
  Valid unique domains : ...
  Invalid/skipped      : ...
  Comment lines        : ...
  Blank lines          : ...

Published ... domains to:
  output/hagezi-pro.txt

HaGeZi Multi PRO: SUCCESS
```

followed by:

```text
======================================================================
StevenBlack Unified
======================================================================

Downloading StevenBlack Unified:
  ...

Parser statistics:
  Valid unique domains : ...
  Invalid/skipped      : ...
  Localhost/system     : ...
  Comment lines        : ...
  Blank lines          : ...

Published ... domains to:
  output/stevenblack-unified.txt

StevenBlack Unified: SUCCESS
```

Finally:

```text
======================================================================
ALL FEEDS SUCCESSFUL
======================================================================
```

---

# Failure Behavior

The two feeds are processed as one GitHub update operation.

Both must successfully pass validation before GitHub commits the generated files.

Conceptually:

```text
HaGeZi PASS
StevenBlack PASS
       |
       v
Commit changes
```

If either feed fails:

```text
HaGeZi PASS
StevenBlack FAIL
       |
       v
NO COMMIT
```

or:

```text
HaGeZi FAIL
       |
       v
NO COMMIT
```

The GitHub Action is marked as failed.

The previously committed output files remain available to Cato.

This prevents an upstream failure from removing the existing blocklists.

---

# Safety Checks

The normalizer does not blindly publish whatever it downloads.

## HaGeZi Minimum Size

The expected minimum is configured as:

```python
"minimum_domains": 100_000
```

If HaGeZi unexpectedly produces fewer than 100,000 valid domains, the update fails.

---

## StevenBlack Minimum Size

The expected minimum is configured as:

```python
"minimum_domains": 40_000
```

If StevenBlack unexpectedly produces fewer than 40,000 valid domains, the update fails.

---

## Previous-List Comparison

Both feeds also use:

```python
MINIMUM_SIZE_RATIO = 0.70
```

This means the new list must contain at least 70% as many entries as the previous version.

For example:

```text
Previous:
220,000

New:
218,000

Result:
ACCEPT
```

But:

```text
Previous:
220,000

New:
15,000

Result:
REJECT
```

---

# Atomic File Replacement

The script writes to a temporary file before replacing the existing output.

Conceptually:

```text
New blocklist
     |
     v
temporary file
     |
     | successful write
     v
replace existing file
```

This prevents a partially written blocklist from replacing a working file.

---

# Git Commit Behavior

Both generated files are staged:

```bash
git add output/hagezi-pro.txt
git add output/stevenblack-unified.txt
```

Git then checks whether anything actually changed.

If neither list changed:

```text
No blocklist changes.
```

No commit is created.

If one or both changed:

```text
Blocklists changed. Committing updates.
```

GitHub creates:

```text
Update Cato blocklists
```

and pushes the changes to the repository.

---

# GitHub Raw URLs

Cato should use the **raw GitHub URLs**, not the regular GitHub file-viewer URLs.

## HaGeZi

Format:

```text
https://raw.githubusercontent.com/<USERNAME>/<REPOSITORY>/main/output/hagezi-pro.txt
```

Example:

```text
https://raw.githubusercontent.com/mnn-github/cato-blocklist/main/output/hagezi-pro.txt
```

---

## StevenBlack

Format:

```text
https://raw.githubusercontent.com/<USERNAME>/<REPOSITORY>/main/output/stevenblack-unified.txt
```

Example:

```text
https://raw.githubusercontent.com/mnn-github/cato-blocklist/main/output/stevenblack-unified.txt
```

Before configuring Cato, open each raw URL in a private/incognito browser window.

The domain lists should load without authentication.

---

# Cato Configuration

Create two independent FQDN Containers.

## Container 1 - HaGeZi

Example:

```text
Name:
HaGeZi Multi PRO

Type:
FQDN

Source:
Sync file from URL

URL:
https://raw.githubusercontent.com/<USERNAME>/<REPOSITORY>/main/output/hagezi-pro.txt
```

---

## Container 2 - StevenBlack

Example:

```text
Name:
StevenBlack Unified

Type:
FQDN

Source:
Sync file from URL

URL:
https://raw.githubusercontent.com/<USERNAME>/<REPOSITORY>/main/output/stevenblack-unified.txt
```

Use **Test Container/Test Connection** before saving each Container.

---

# Cato Sync Interval

The Cato Container synchronization interval is independent of the GitHub Actions schedule.

For example:

```text
03:17
GitHub generates latest lists

06:00
Cato synchronizes Containers

12:00
Cato synchronizes Containers

18:00
Cato synchronizes Containers
```

GitHub does not regenerate the files when Cato accesses them.

Cato simply retrieves the latest version already published to GitHub.

A Cato synchronization interval such as:

```text
6 hours
```

provides a reasonable balance for these types of lists.

A 24-hour interval can also be used if once-daily synchronization is sufficient.

---

# Internet Firewall Policy

Each Container can be referenced independently by the Cato Internet Firewall.

Example:

```text
1. Block HaGeZi Multi PRO
       Destination: HaGeZi Multi PRO
       Action: Block

2. Block StevenBlack Unified
       Destination: StevenBlack Unified
       Action: Block
```

An exception rule can be placed above these rules:

```text
1. Blocklist Exceptions       ALLOW

2. HaGeZi Multi PRO           BLOCK

3. StevenBlack Unified        BLOCK

4. Remaining policy...
```

This provides a convenient way to resolve false positives without modifying the generated files.

---

# False Positives

If an application stops working:

1. Review Cato events.
2. Identify the blocked destination FQDN.
3. Determine which Container matched it.
4. Confirm that the domain is legitimately required.
5. Add the FQDN to an appropriate Allow/Exception rule above the blocklist rules.

Do not manually remove domains from:

```text
output/hagezi-pro.txt
```

or:

```text
output/stevenblack-unified.txt
```

because the files are regenerated during the next update.

---

# Verifying Scheduled Execution

Navigate to:

```text
Repository
  -> Actions
  -> Update Cato Blocklists
```

A manually started run shows:

```text
workflow_dispatch
```

An automatically scheduled run shows:

```text
schedule
```

This provides confirmation that GitHub's scheduler triggered the workflow.

---

# Changing the Schedule

The schedule can be changed by editing:

```text
.github/workflows/update-blocklist.yml
```

For example:

```yaml
- cron: "30 20 * * *"
  timezone: "America/New_York"
```

would schedule the workflow for:

```text
8:30 PM Eastern
```

Commit the YAML change to the default branch.

No manual workflow execution is required after changing the schedule.

GitHub automatically uses the new schedule after the updated workflow is committed.

---

# Testing the Scheduler

To verify automatic scheduling without waiting until 3:17 AM:

1. Determine a time approximately 10-15 minutes in the future.
2. Temporarily change the cron schedule.
3. Commit the change to `main`.
4. Wait for the workflow to run automatically.
5. Confirm the trigger is `schedule`.
6. Restore the normal schedule.

Normal schedule:

```yaml
- cron: "17 3 * * *"
  timezone: "America/New_York"
```

Scheduled workflows can occasionally start a few minutes later than the requested time.

---

# Normal Daily Operation

Once configured, no manual intervention should normally be required.

```text
                 DAILY AT 03:17 EASTERN

                         |
                         v
                  GitHub Actions
                         |
                         v
                   normalize.py
                         |
              +----------+----------+
              |                     |
              v                     v
          HaGeZi                StevenBlack
              |                     |
              v                     v
          Validate               Validate
              |                     |
              v                     v
         Normalize               Normalize
              |                     |
              v                     v
      hagezi-pro.txt      stevenblack-unified.txt
              |                     |
              +----------+----------+
                         |
                         v
                  GitHub Commit
                   if changed
                         |
              +----------+----------+
              |                     |
              v                     v
        Cato Container        Cato Container
              |                     |
              +----------+----------+
                         |
                         v
                  Internet Firewall
```

---

# Troubleshooting

## GitHub Action fails during normalization

Open:

```text
Repository
  -> Actions
  -> failed run
  -> Download and normalize blocklists
```

Review the Python output.

The script identifies which feed failed.

---

## Cato cannot download a list

Verify the URL starts with:

```text
https://raw.githubusercontent.com/
```

Open the URL in an incognito/private browser.

It should work without GitHub authentication.

---

## Cato rejects the StevenBlack file

Verify that:

```text
output/stevenblack-unified.txt
```

contains:

```text
ads.example.com
malware.example.net
```

and not:

```text
0.0.0.0 ads.example.com
```

---

## Generated files don't change

This may be completely normal.

If the upstream source has not changed, the generated file remains identical and GitHub intentionally does not create a new commit.

The Action should still show a successful run.

---

## Push fails

Verify:

```yaml
permissions:
  contents: write
```

exists in the workflow.

---

# Security Model

The architecture deliberately places validation between third-party sources and Cato:

```text
Third-party feed
       |
       v
Download
       |
       v
Format-specific parser
       |
       v
FQDN validation
       |
       v
Deduplication
       |
       v
Size sanity check
       |
       v
Known-good output
       |
       v
GitHub
       |
       v
Cato
```

Neither third-party source is treated as implicitly trusted input.

---

# Maintenance

Periodically review:

```text
GitHub
  -> Actions
```

to verify that scheduled executions remain successful.

Also periodically review the Containers in Cato CMA to verify successful URL synchronization.

Git history provides an audit trail showing when either generated blocklist changed.

---

# External Projects

## HaGeZi DNS Blocklists

[https://github.com/hagezi/dns-blocklists](https://github.com/hagezi/dns-blocklists)

## StevenBlack Hosts

[https://github.com/StevenBlack/hosts](https://github.com/StevenBlack/hosts)

## GitHub Actions

[https://github.com/features/actions](https://github.com/features/actions)

## Cato Networks

[https://www.catonetworks.com/](https://www.catonetworks.com/)

---

# Disclaimer

This is an independent integration project and is not an official Cato Networks, HaGeZi, StevenBlack, or GitHub product.

Third-party blocklists can cause legitimate domains or applications to be blocked.

Review Cato events when troubleshooting connectivity and use explicit policy exceptions where appropriate.

Refer to each upstream project for its current licensing terms, documentation, list composition, and usage requirements.

---

# Summary

This project maintains two independent Cato-compatible FQDN blocklists:

```text
HaGeZi Multi PRO
      |
      v
output/hagezi-pro.txt
      |
      v
Cato FQDN Container
```

and:

```text
StevenBlack Unified
      |
      v
output/stevenblack-unified.txt
      |
      v
Cato FQDN Container
```

A single GitHub Action runs:

```text
Daily at 03:17 Eastern
```

and a single:

```text
scripts/normalize.py
```

processes both sources.

The result is an automated, serverless blocklist pipeline:

```text
HaGeZi -----------+
                  |
                  +--> GitHub Actions
                  |        |
StevenBlack ------+        v
                      normalize.py
                          |
                    +-----+-----+
                    |           |
                    v           v
                 HaGeZi     StevenBlack
                    |           |
                    v           v
                 Cato        Cato
               Container    Container
                    |           |
                    +-----+-----+
                          |
                          v
                  Internet Firewall
```

Since this replaces the previous README rather than creating a separate document, I kept the same writing-block ID so you can treat it as the revised version.
