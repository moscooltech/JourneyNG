# Privacy

Privacy is a product requirement (spec §29, §64). This system is **temporary, explicit, purpose-bound journey sharing** — not surveillance.

## Principles → implementation

| Principle | Implementation |
|---|---|
| Purpose limitation | Consent record carries purpose `TRAVEL_TO_DESTINATION` only |
| Data minimization | Only one latest point per participant; no history table |
| Explicit consent | `location_consents` row required on **every** ingestion/viewer path |
| Transparency | Persistent notification names who sees the location; privacy dashboard lists active sharing |
| Revocation | Stop Sharing, Leave, Stop All Sharing — immediate, server-enforced |
| Storage limitation | Redis TTLs; `location_latest` deleted after `LOCATION_RETENTION_HOURS`; arrival revokes consent |
| Access control | Host-only viewer (V1); server derives identity; IDOR-tested |
| Security | Hashed tokens, Argon2id passwords, rotation with reuse detection |
| Accountability | Audit logs without raw GPS/credentials |

## Retention rules

- Live location: Redis with TTL; single `location_latest` row per participant.
- Cleanup worker deletes location rows older than the retention window.
- After journey end: sharing stops automatically; consent records become `REVOKED`/`EXPIRED`; no further location accepted.
- Audit metadata: journey-level events only — never coordinates.

## Account deletion (spec §30)

`DELETE /me` deactivates the account, cancels hosted journeys, revokes consents and sessions, anonymizes identity fields (`email/phone/hash → NULL`, display name → "Deleted User"). Legally-required records (minimal metadata) may be retained per policy.

## Nigeria Data Protection Act 2023

Before public production release: complete legal/privacy review under NDPA 2023 and NDPC guidance. Technical controls here do **not** by themselves constitute legal compliance. Required artifacts before launch: Privacy Policy, Terms of Service, Location Sharing Explanation, Data Retention Policy, Account Deletion Policy. Child/minor features require a separate child-data design and legal review.
