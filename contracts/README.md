# sg-ai Contracts

Smart Guitar AI Coach schema contracts.

## Schemas

| Schema | Purpose |
|--------|---------|
| `coach_context_packet_v1.json` | Input context for coaching jobs |
| `coaching_draft_v1.json` | Output from coaching jobs |

## Governance

- **No PII fields** — Schemas explicitly block player_id, account_id, email, etc.
- **Local runtime only** — model.runtime must be "local"
- **Evidence-cited feedback** — Every feedback item must cite metrics

## Source of Truth

The authoritative schemas live in `sg-spec/contracts/`. These are vendored copies.

Update process:
1. Change schema in sg-spec
2. Run schema parity gate
3. Update vendored copy here
