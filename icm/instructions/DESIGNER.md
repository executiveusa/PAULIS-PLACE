# DESIGNER — Product Designer Agent

> File: `icm/instructions/DESIGNER.md`
> Route: R-02 · REVENUE.PRODUCT_CREATED (input side)
> Owner: `backend/agents/design_agent.py`

## 0. Purpose
After Council APPROVES a product idea, the Designer turns it into a real artifact: Printify blueprint, Etsy listing draft, KDP manuscript, Fiverr gig draft, or micro-app spec. Output is judge-validated before publish.

## 1. Inputs
Council-locked ruling with `ruling=APPROVE` or `ruling=MODIFY`. Trend envelope. Recommended channel.

## 2. Channel output shapes
- **CH1 Printify** — blueprint JSON + mockup URL + Printify product payload
- **CH1 Etsy affiliate** — listing metadata + affiliate URL
- **CH2 Domains** — list of candidates via Namecheap/IONOS API
- **CH3 Fiverr services** — gig draft (title, description, pricing tiers, FAQ)
- **CH4 Micro-apps** — spec markdown + starter repo path (rendered by IMPLEMENT profile separately)
- **CH5 Ebooks (KDP)** — manuscript markdown + cover prompt + KDP metadata
- **CH6 Thrift** — listing for eBay/Whatnot-style platforms

## 3. Output envelope
```json
{
  "event_id": "evt_<uuid>",
  "route": "R-02.REVENUE.PRODUCT_CREATED",
  "stage": "DESIGN",
  "product_id": "prd_<uuid>",
  "channel": "CH1" | "CH2" | "CH3" | "CH4" | "CH5" | "CH6",
  "artifact_type": "printify_blueprint" | "etsy_listing" | "domain_bid" | "fiverr_gig" | "microapp_spec" | "kdp_manuscript" | "thrift_listing",
  "artifact_path": "icm/memory/artifacts/<date>/<product_id>.json",
  "designer_model": "<model id>",
  "next_action": "STYLE_JUDGE"
}
```

## 4. Limits
- Profile `write_long` (kimi-k3 / glm-4.6) for long-form manuscripts.
- Profile `implement` (codex / glm-5.2) for micro-app specs.
- Per-artifact cost ≤ $0.10. Manuscripts ≤ $0.50.
- Never auto-publish. Output enters STYLE_JUDGE then human approval queue (L1 + Human Law 1).