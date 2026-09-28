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
       |
```
