# PRINTED CLIs — Agent Tool Surface (cli-printing-press integration)

> File: `icm/context/PRINTED_CLIS.md`
> Architecture: every Yappyverse agent that touches an external API SHOULD do so by shelling out
> to the matching printed Go CLI built by [cli-printing-press](https://github.com/mvanhorn/cli-printing-press).

## Why a printed-CLI surface (not direct REST)

| property | direct REST wrapper | printed Go CLI |
|---|---|---|
| token cost per call | high (model reads raw JSON) | low (`--agent` => compact JSON, typed exit codes) |
| local cache | none | SQLite + FTS5 per printed CLI |
| compound queries (health, reconcile, bottleneck, stale) | impossible | possible (data is local) |
| error mode | text parsing | typed exit codes 0/2/3/4/5/7 |
| output mode | one | many: `--json --compact --csv --select --quiet --dry-run` |
| auth | per service, per call | env var, set once |
| MCP surface | DIY | printed CLIs ship their own MCP server (`<api>-pp-mcp`) for IDE agents |
| lifetime | dies with binary | lives forever — `go build` once, shell forever |

## Backend wrapper
`backend/services/printed_cli.py` exposes:
  - `await call_printed("printify", ["shops-json", "--compact"])`
  - `await printify_sync()` / `printify_search(query)` / `printify_workflow(name)`
  - `doctor_all()` — runs `doctor` on every installed printed CLI

L4 enforced: wrapper scans args for `sk_`/`ghp_`/`sbp_`/`r8_`/`rk_live_`/`Bearer` and rejects before spawn.

## REST API surface
- `GET /api/printed-clis` — list all known + their install state
- `POST /api/printed-clis/{name}/sync` — sync local SQLite cache
- `GET  /api/printed-clis/{name}/doctor` — verify auth
- `GET  /api/printed-clis/{name}/search?q=...` — FTS5 search
- `GET  /api/printed-clis/{name}/which?capability=...` — find command by capability

## Print queue (current status)
| API | status | OpenAPI spec source | env var |
|---|---|---|---|
| printify | **PRINTED + BUILD PASSING** | https://developers.printify.com/openapi.json | `PRINTIFY_TOKEN` |
| etsy | pending | https://developer.etsy.com — 403'ed; need direct OpenAPI spec | `ETSY_API_KEY` |
| creem | pending | https://docs.creem.io — no browsable docs found; manual spec needed | `CREEM_API_KEY` |
| zernio | pending | https://api.zernio.com/v1 — only REused from inline code; capture via browser-sniff | `ZERNIO_API_TOKEN` |
| openrouter | pending | https://openrouter.ai/api/v1/spec.json (auto-fetch when agent needs) | `OPENROUTER_API_KEY` |
| trends | pending | none published — uses pytrends + Firecrawl as upstreams; skip printing, too thin | — |
| fiverr | pending | limited API; capture H1 HAR via browser-sniff gate | `FIVERR_ACCESS_TOKEN` |
| btcpay | pending | OpenAPI at <btcpay_url>/api/v1/swagger.json once configured | `BTCPAY_API_KEY` |

## How to print the next one
From the repo root:

```sh
# Ensure Go 1.26.5+ and the cli-printing-press binary are installed.
cli-printing-press --version    # >= 4.30.1

# Generate a CLI from an OpenAPI spec:
cli-printing-press generate --spec "<openapi.json URL>" \
  --name <api> \
  --validate=false \
  --output ./printed-clis/<api>

# Add the entry to PRINTED_REGISTRY in backend/services/printed_cli.py
# Build the binary:
cd ./printed-clis/<api>
go mod tidy
go build -o <api>-pp-cli.exe ./cmd/<api>-pp-cli/

# Self-test:
./<api>-pp-cli.exe doctor
./<api>-pp-cli.exe --help
```

Once a new CLI is built, the observation page automatically picks it up via
`GET /api/printed-clis`. The nightly self-improvement loop will propose PRs
that swap bare Python REST calls for printed-CLI shellouts based on the
"bottleneck → use_cli_search" pattern it detects in ops reports.

## Why printed CLIs solve bottlenecks, bloat, and revenue
- **Bottlenecks**: `health`, `bottleneck`, `reconcile`, `stale` compound commands only work because data lives in local SQLite. No stateless wrapper can compute them.
- **Bloat**: the wrapper is ~80 lines of code. We replace 800-line Printify/ Etsy/Fiverr REST clients with two-line shellouts.
- **Revenue on autopilot**: each printed CLI ships with `import`/`export`, `tail`, `analytics`, and `workflow` commands. A Yappyverse agent can run `analytics` Printify to find high-margin blueprints offline in 50ms vs 3 seconds hit-and-hope per REST call.