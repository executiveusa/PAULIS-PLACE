# Composio Integration — Pauli Integrations Bus

Composio is the default broad SaaS integration provider for Pauli's Place. It is **not** the control plane and does not own mission authority, tenant policy, budgets, approvals, or memory.

## Why it exists

Agents should be able to discover and connect to tools without every app becoming bespoke integration code. Composio sessions provide runtime tool discovery, per-user authentication, connected-account scoping, hosted MCP endpoints, triggers, and tool execution.

## Pauli rules

1. **Strict tenant identity.** Every tenant/actor pair maps to a stable opaque Composio entity ID.
2. **Read-first autonomy.** Autonomous sessions use Composio's `readOnlyHint` tag restriction.
3. **Action sessions are explicit.** Write-capable sessions require a toolkit allowlist plus a scoped Pauli approval.
4. **Human authentication remains human.** Agents may request a connection link; the person authorizes OAuth/API access.
5. **No secrets in the world/UI.** Status exposes only configured/not-configured.
6. **MCP is the common runtime seam.** Any MCP-capable agent runtime can consume a session endpoint.
7. **Composio is replaceable.** Direct native adapters remain possible for critical/high-volume integrations.

## Typical lifecycle

```text
Mission needs Gmail/Notion/GitHub/etc.
        ↓
Pauli checks tenant connection
        ↓
create READ session (autonomous)
        ↓
agent discovers tools at runtime
        ↓
not connected?
        ↓
Pauli produces connection URL for human
        ↓
human authenticates once
        ↓
read/research continues autonomously
        ↓
write/send action required
        ↓
Pauli approval policy
        ↓
scoped approval exists?
        ├── no → WAITING_APPROVAL
        └── yes
              ↓
        ACTION session limited to approved toolkit(s)
              ↓
        execute + audit + evidence
```

## Environment

```bash
COMPOSIO_API_KEY=...
```

Never commit the key.

## API

- `GET /api/integrations/composio/status`
- `POST /api/integrations/composio/sessions/read`
- `POST /api/integrations/composio/sessions/{session_id}/connect`

Arbitrary write execution is intentionally **not** exposed as a browser endpoint. Mission workers obtain action sessions through the governance layer.
