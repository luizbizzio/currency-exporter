# Security Policy

## Supported Versions

This is a personal open-source project maintained on a best-effort basis.

Security fixes are typically provided for:

- the latest released version
- the current `main` branch (when feasible)

| Version | Supported |
| ------- | --------- |
| Latest released version | ✅ |
| `main` | ✅ Best effort |
| Older releases | ❌ |

## Reporting a Vulnerability

If you believe you found a security issue, please **do not open a public issue**.

### Preferred method
Use **GitHub Security Advisories** (private vulnerability reporting) for this repository.

### Alternative method
If private reporting is not available, contact the maintainer privately (for example, via the email listed on the GitHub profile, if available).

## What to Include in the Report

Please include as much of the following as possible:

- A clear description of the issue
- Affected version/tag/commit
- Steps to reproduce (proof-of-concept if possible)
- Expected behavior vs actual behavior
- Impact assessment (what an attacker can do)
- Environment details (OS, Python version, container or bare metal)
- Any suggested fix or mitigation (optional)

## Response Expectations

This is a best-effort project.

Targets (not guarantees):

- Initial acknowledgment: within **7 days**
- Follow-up / triage update: as available
- Fix timeline: depends on severity and maintainer availability

## Scope Notes

This project is a **read-only Prometheus exporter** that periodically fetches currency data from a public JSON endpoint and exposes derived exchange-rate metrics.

Typical security-relevant areas include:

- unintended exposure of the metrics HTTP endpoint on untrusted networks
- denial-of-service (DoS) via excessive configuration size or scrape/update behavior
- supply-chain risks from third-party dependencies and upstream data sources
- log output accidentally revealing internal details (IPs/hostnames, deployment paths)

This exporter does **not** handle user accounts, authentication, payments, or secrets by default.

## Security Considerations

### 1) Network exposure
The exporter exposes an HTTP server (Prometheus metrics). By default, this endpoint has **no authentication**.

Recommendations:

- **Do not expose** the exporter port publicly on the Internet
- Restrict access to trusted networks only (LAN/VPN)
- Use a firewall rule or bind only to a trusted interface if supported by your deployment
- If remote access is required, place it behind a reverse proxy that enforces authentication and TLS

### 2) Upstream data source and integrity
The exporter fetches currency data from a third-party endpoint:

- `cdn.jsdelivr.net` (jsDelivr CDN)
- the dataset package `@fawazahmed0/currency-api`

Implications:

- availability depends on the upstream service and the CDN
- data can change over time and may be temporarily inconsistent
- requests are over HTTPS, but the exporter does not pin certificates or validate dataset integrity beyond JSON parsing

Recommendations:

- consider running behind an egress-allowlist (only allow HTTPS to trusted domains)
- consider pinning to a specific dataset version (instead of `@latest`) if you need stability
- monitor exporter `*_up` and error metrics to detect upstream failures

### 3) Denial of service / resource usage
Risk factors:

- very large `pairs` lists increase metric cardinality and CPU usage
- short update intervals increase outbound requests and load
- aggressive Prometheus scrape intervals can increase local load

Recommendations:

- keep the number of pairs reasonable
- avoid extremely low `update_interval_seconds`
- scrape at a sensible interval (for example 15–60 seconds) and rely on exporter caching

### 4) Logging
The exporter logs errors and configuration validation warnings.

Recommendations:

- treat logs as operational data
- avoid publishing logs that include deployment details

## Non-goals

This project does not attempt to provide:

- authentication/authorization for the metrics endpoint
- encryption beyond standard HTTPS used when fetching upstream data
- tamper-proof integrity guarantees for upstream currency values

If you need a hardened setup, deploy behind a secure network boundary and/or authenticated reverse proxy.

## Responsible Disclosure

Please allow reasonable time for triage and a fix before public disclosure.
If a vulnerability affects many users or has active exploitation potential, include that context in your report.
