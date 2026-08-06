# Printify2 CLI

## Getting started

Printify API enables you to automate product and order creation for a variety of scenarios,
including integration with your on-site design generator, on-site product customization and more.

Created by [@executiveusa](https://github.com/executiveusa) (openhands).

## Install

The recommended path installs both the `printify2-pp-cli` binary and the `pp-printify2` agent skill (Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, and other agents supported by the upstream [`skills`](https://github.com/vercel-labs/skills) CLI) in one shot:

```bash
npx -y @mvanhorn/printing-press-library install printify2
```

For CLI only (no skill):

```bash
npx -y @mvanhorn/printing-press-library install printify2 --cli-only
```

For skill only — installs the skill into the same agents as the default command above, but skips the CLI binary (use this to update or reinstall just the skill):

```bash
npx -y @mvanhorn/printing-press-library install printify2 --skill-only
```

To constrain the skill install to one or more specific agents (repeatable — agent names match the [`skills`](https://github.com/vercel-labs/skills) CLI):

```bash
npx -y @mvanhorn/printing-press-library install printify2 --agent claude-code
npx -y @mvanhorn/printing-press-library install printify2 --agent claude-code --agent codex
```

### Without Node

The generated install path is category-agnostic until this CLI is published. If `npx` is not available before publish, install Node or use the category-specific Go fallback from the public-library entry after publish.

### Pre-built binary

Download a pre-built binary for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/printify2-current). On macOS, clear the Gatekeeper quarantine: `xattr -d com.apple.quarantine <binary>`. On Unix, mark it executable: `chmod +x <binary>`.

<!-- pp-hermes-install-anchor -->
## Install for Hermes

Install the CLI binary first. The installer writes binaries to a per-user managed bin directory by default: `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows.

```bash
npx -y @mvanhorn/printing-press-library install printify2 --cli-only
```

Then install the focused Hermes skill.

From the Hermes CLI:

```bash
hermes skills install mvanhorn/printing-press-library/cli-skills/pp-printify2 --force
```

Inside a Hermes chat session:

```bash
/skills install mvanhorn/printing-press-library/cli-skills/pp-printify2 --force
```

Restart the Hermes session or gateway if the newly installed skill is not visible immediately.

## Install for OpenClaw
Install both the CLI binary and the focused OpenClaw skill. The installer defaults binaries to a per-user bin directory (`$HOME/.local/bin` on macOS/Linux, `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows):

```bash
npx -y @mvanhorn/printing-press-library install printify2 --agent openclaw
```

Restart the OpenClaw session or gateway if the newly installed skill is not visible immediately.

## Use with Claude Desktop

This CLI ships an [MCPB](https://github.com/modelcontextprotocol/mcpb) bundle — Claude Desktop's standard format for one-click MCP extension installs (no JSON config required).

To install:

1. Download the `.mcpb` for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/printify2-current).
2. Double-click the `.mcpb` file. Claude Desktop opens and walks you through the install.
3. Fill in `PRINTIFY2_BEARER_AUTH` when Claude Desktop prompts you.

Requires Claude Desktop 1.0.0 or later. Pre-built bundles ship for macOS Apple Silicon (`darwin-arm64`) and Windows (`amd64`, `arm64`); for other platforms, use the manual config below.

<details>
<summary>Manual JSON config (advanced)</summary>

If you can't use the MCPB bundle (older Claude Desktop, unsupported platform), install the MCP binary and configure it manually.


Install the MCP binary from this CLI's published public-library entry or pre-built release.

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "printify2": {
      "command": "printify2-pp-mcp",
      "env": {
        "PRINTIFY2_SHOP_ID": "<shop_id>",
        "PRINTIFY2_BEARER_AUTH": "<your-key>"
      }
    }
  }
}
```

</details>

## Quick Start

### 1. Install

See [Install](#install) above.

### 2. Set Up Credentials

Get your access token from your API provider's developer portal, then store it:

```bash
printify2-pp-cli auth set-token YOUR_TOKEN_HERE
```

Or set it via environment variable:

```bash
export PRINTIFY2_BEARER_AUTH="your-token-here"
```

### 3. Verify Setup

```bash
printify2-pp-cli doctor
```

This checks your configuration and credentials.

### 4. Try Your First Command

```bash
printify2-pp-cli catalog retrieve-alist-of-all-print-providers-that-fulfill-orders-for-aspecific-blueprint mock-value
```

## Usage

Run `printify2-pp-cli --help` for the full command reference and flag list.

## Paths & environment variables

This CLI separates local files into four path kinds:

| Kind | Contents |
|------|----------|
| `config` | User-editable settings such as `config.toml` and saved profiles |
| `data` | Durable local data: `credentials.toml`, `data.db`, cookies, browser-session proof files, and other auth sidecars |
| `state` | Runtime state such as persisted queries, jobs, and `teach.log` |
| `cache` | Regenerable HTTP/cache files |

Each kind resolves independently. The ladder is:

1. Per-kind env var: `PRINTIFY2_CONFIG_DIR`, `PRINTIFY2_DATA_DIR`, `PRINTIFY2_STATE_DIR`, or `PRINTIFY2_CACHE_DIR`
2. `--home <dir>` for this invocation
3. `PRINTIFY2_HOME` for a flat relocated root
4. XDG env vars: `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME`
5. Platform defaults matching existing installs

For containers and agent sandboxes, prefer a single relocated root:

```bash
export PRINTIFY2_HOME=/srv/printify2
printify2-pp-cli doctor
```

Under `PRINTIFY2_HOME=/srv/printify2`, the four dirs resolve to `/srv/printify2/config`, `/srv/printify2/data`, `/srv/printify2/state`, and `/srv/printify2/cache`.

MCP servers do not receive CLI flags from the host. Put relocation in the host `env` block:

```json
{
  "mcpServers": {
    "printify2": {
      "command": "printify2-pp-mcp",
      "env": {
        "PRINTIFY2_HOME": "/srv/printify2"
      }
    }
  }
}
```

Precedence matters in fleets: an ambient per-kind variable such as `PRINTIFY2_DATA_DIR` overrides an explicit `--home` for that kind. Use `PRINTIFY2_HOME` or the per-kind variables for durable fleet relocation; treat `--home` as the weaker per-invocation lever.

Relocation is one-way. Unsetting `PRINTIFY2_HOME` does not move files back to platform defaults, and `doctor` cannot find credentials left under a former root. Move the files manually before unsetting relocation variables.

Existing installs keep working because the platform-default rung matches the legacy layout. On the first auth write, stored secrets leave `config.toml` and are consolidated into `credentials.toml` under the data directory. Run `printify2-pp-cli doctor --fail-on warn` to check path and credential-location warnings in automation.

## Commands

### catalog

Browse the Printify catalog including blueprints, print providers, product variants, and shipping information. Explore available products and their customization options.

- **`printify2-pp-cli catalog retrieve-alist-of-all-print-providers-that-fulfill-orders-for-aspecific-blueprint`** - Retrieve a list of all print providers that fulfill orders for a specific blueprint
- **`printify2-pp-cli catalog retrieve-alist-of-available-print-providers`** - Retrieves the list of blueprints in the catalog to explore from
- **`printify2-pp-cli catalog retrieve-alist-of-variants-of-ablueprint-from-aspecific-print-provider`** - Retrieves the list of of variants options for the Print Provider and Blueprint.
    Those form the set of options available for customization Product (Blueprint)
    on particular manufacturer (Print Provider).
- **`printify2-pp-cli catalog retrieve-aspecific-blueprint`** - Retrieves the list of blueprints in the catalog to explore from
- **`printify2-pp-cli catalog retrieve-aspecific-print-provider`** - Retrieves the list of blueprints in the catalog to explore from
- **`printify2-pp-cli catalog retrieve-available-shipping-list-information`** - Retrieves the list of print providers avilable for the Blueprint
- **`printify2-pp-cli catalog retrieve-economy-shipping-method-information`** - Retrieves the list of print providers available for the Blueprint
- **`printify2-pp-cli catalog retrieve-express-shipping-method-information`** - Retrieves the list of print providers available for the Blueprint
- **`printify2-pp-cli catalog retrieve-priority-shipping-method-information`** - Retrieves the list of print providers available for the Blueprint
- **`printify2-pp-cli catalog retrieve-shipping-information`** - Retrieves the list of print providers avilable for the Blueprint
- **`printify2-pp-cli catalog retrieve-specific-shipping-method-information`** - Retrieves the list of print providers avilable for the Blueprint
- **`printify2-pp-cli catalog retrieves-list-of-blueprints-in-the`** - Retrieves the list of blueprints in the catalog to explore from

### shops

Manage Printify shops and shop connections. Retrieve shop information and disconnect shops from your account.


### shops-json

Manage shops json

- **`printify2-pp-cli shops-json`** - This will return the list of available merchant shops (IDs and titles)

### uploads

Upload and manage images and assets. Upload images from URLs or base64-encoded content, retrieve upload information, and archive uploaded images.

- **`printify2-pp-cli uploads an-image`** - Upload an image
- **`printify2-pp-cli uploads retrieve-an-uploaded-image-by-id`** - Retrieve an uploaded image by id

### uploads-json

Manage uploads json

- **`printify2-pp-cli uploads-json`** - Retrieve a list of uploaded images


### Self-learning loop

This CLI caches per-question discovery so repeat queries skip the walk and structurally similar queries get answered via entity substitution. The loop also self-captures: every invocation is journaled locally, and failed-flag corrections plus fresh teaches surface as candidates on the next `recall` for confirm/reject judgment. Agents call `recall` before discovery and fire `teach &` after answering. See the `## Automatic learning` section in `SKILL.md` for the full protocol.

- **`printify2-pp-cli recall <query>`** - Look up cached resources for a query before running discovery
- **`printify2-pp-cli teach`** - Record a query -> resource mapping (silent on success, safe to background with `&`)
- **`printify2-pp-cli learnings list`** - Inspect taught rows
- **`printify2-pp-cli learnings forget <query>`** - Undo a teach
- **`printify2-pp-cli learnings candidates`** - List auto-captured candidates awaiting confirm/reject
- **`printify2-pp-cli learnings stats`** - Local loop metrics: recall hit rate, teach-to-reuse, playbook resolution, candidate counts
- **`printify2-pp-cli teach-pattern`** - Install a query/resource template up front
- **`printify2-pp-cli teach-lookup`** - Add an entity mapping (e.g. country code, team alias) for pattern substitution

Pass `--no-learn` or set `PRINTIFY2_NO_LEARN=true` to disable the loop for deterministic flows.

The local store's schema version stamp is one-way: once this version of `printify2-pp-cli` opens the database, older binaries refuse it with a version error — upgrade the binary rather than downgrading.

## Output Formats

```bash
# Human-readable table (default in terminal, JSON when piped)
printify2-pp-cli catalog retrieve-alist-of-all-print-providers-that-fulfill-orders-for-aspecific-blueprint mock-value

# JSON for scripting and agents
printify2-pp-cli catalog retrieve-alist-of-all-print-providers-that-fulfill-orders-for-aspecific-blueprint mock-value --json

# Filter to specific fields
printify2-pp-cli catalog retrieve-alist-of-all-print-providers-that-fulfill-orders-for-aspecific-blueprint mock-value --json --select id,name,status

# Dry run — show the request without sending
printify2-pp-cli catalog retrieve-alist-of-all-print-providers-that-fulfill-orders-for-aspecific-blueprint mock-value --dry-run

# Agent mode — JSON + compact + no prompts in one flag
printify2-pp-cli catalog retrieve-alist-of-all-print-providers-that-fulfill-orders-for-aspecific-blueprint mock-value --agent
```

## Agent Usage

This CLI is designed for AI agent consumption:

- **Non-interactive** - never prompts, every input is a flag
- **Pipeable** - `--json` output to stdout, errors to stderr
- **Filterable** - `--select id,name` returns only fields you need
- **Previewable** - `--dry-run` shows the request without sending
- **Explicit retries** - add `--idempotent` to create retries and add `--ignore-missing` to delete retries when a no-op success is acceptable
- **Confirmable** - `--yes` for explicit confirmation of destructive actions
- **Piped input** - write commands can accept structured input when their help lists `--stdin`
- **Offline-friendly** - sync/search commands can use the local SQLite store when available
- **Agent-safe by default** - no colors or formatting unless `--human-friendly` is set

Exit codes: `0` success, `2` usage error, `3` not found, `4` auth error, `5` API error, `7` rate limited, `10` config error.

## Runtime Endpoint

This CLI resolves endpoint placeholders at runtime, so one installed binary can target different tenants or API versions without regeneration.

Endpoint environment variables:
- `PRINTIFY2_SHOP_ID` resolves `{shop_id}`

Base URL: `https://api.printify.com`

## Health Check

```bash
printify2-pp-cli doctor
```

Verifies configuration, credentials, and connectivity to the API.

## Configuration

Run `printify2-pp-cli doctor` to see the resolved config, data, state, and cache directories. The platform-default config path is `~/.config/printify-public-pp-cli/config.toml`; `--home`, `PRINTIFY2_HOME`, and per-kind env vars can relocate it.

Static request headers can be configured under `headers`; per-command header overrides take precedence.

Environment variables:

| Name | Kind | Required | Description |
| --- | --- | --- | --- |
| `PRINTIFY2_SHOP_ID` | endpoint | Yes |  |
| `PRINTIFY2_BEARER_AUTH` | per_call | Yes | Set to your API credential. |

### agentcookie (optional)

If you use agentcookie to sync secrets across machines, this CLI auto-adopts agentcookie-managed credentials with no extra setup. When the daemon writes to this CLI's config, `printify2-pp-cli doctor` reports `agentcookie: detected` and `auth-status` labels the source as `agentcookie`. Skip this section if you don't use agentcookie - the CLI works the same as any other.

## Troubleshooting
**Authentication errors (exit code 4)**
- Run `printify2-pp-cli doctor` to check credentials
- Verify the environment variable is set: `echo $PRINTIFY2_BEARER_AUTH`
**Not found errors (exit code 3)**
- Check the resource ID is correct
- Run the `list` command to see available items

---

Generated by [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press)
