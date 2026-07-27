# Security Policy

## Supported Versions

This is a portfolio/research project, not a maintained product with an LTS policy. Security fixes are
made against the latest commit on `main`.

| Version | Supported |
|---------|-----------|
| latest (`main`) | ✅ |
| tagged releases prior to latest | ❌ |

## Reporting a Vulnerability

Please **do not open a public GitHub issue** for security vulnerabilities.

Instead, report it privately via [GitHub Security Advisories](../../security/advisories/new) for this
repository, or email junaid.ahmedjn015@gmail.com with:

- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal repro is very helpful)
- Any suggested fix, if you have one

You can expect an acknowledgment within a few days. This is a solo-maintained project, so response time
isn't guaranteed on a fixed SLA, but reports are taken seriously and credited in the fix.

## Scope Notes

- The API has no authentication/session layer by design (see `PLANNING.md`) — do not deploy this as-is
  behind a public endpoint without adding your own auth layer.
- `.env` holds a real Mistral API key in local/deployed use; it is gitignored and must never be committed.
  If you find a key accidentally committed anywhere in this repo's history, please report it as above so it
  can be rotated and the history scrubbed.
