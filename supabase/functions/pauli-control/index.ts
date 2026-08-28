import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import postgres from "npm:postgres@3.4.7";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, content-type, apikey, x-client-info",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
};

const sql = postgres(Deno.env.get("SUPABASE_DB_URL")!, { prepare: false, max: 1 });

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: cors });
}

async function getUserId(req: Request): Promise<string | null> {
  const auth = req.headers.get("Authorization") ?? "";
  if (!auth.startsWith("Bearer ")) return null;
  const token = auth.slice(7);
  const url = `${Deno.env.get("SUPABASE_URL")}/auth/v1/user`;
  const pub = JSON.parse(Deno.env.get("SUPABASE_PUBLISHABLE_KEYS") ?? "{}")?.default ?? Deno.env.get("SUPABASE_ANON_KEY");
  const response = await fetch(url, { headers: { Authorization: `Bearer ${token}`, apikey: pub ?? "" } });
  if (!response.ok) return null;
  const user = await response.json();
  return user?.id ?? null;
}

async function membership(orgSlug: string, userId: string) {
  const rows = await sql`
    select o.id as organization_id, m.role
    from pauli.organizations o
    join pauli.memberships m on m.organization_id=o.id
    where o.slug=${orgSlug} and o.status='active' and m.user_id=${userId}::uuid and m.status='active'
    limit 1
  `;
  return rows[0] ?? null;
}

async function overview(orgId: string) {
  const metrics = (await sql`
    select
      (select count(*)::int from pauli.missions where organization_id=${orgId}::uuid and status not in ('CLOSED','CANCELLED','FAILED')) active_missions,
      (select count(*)::int from pauli.agents where organization_id=${orgId}::uuid and status in ('working','meeting','recovering')) agents_working,
      (select count(*)::int from pauli.approvals where organization_id=${orgId}::uuid and status='pending') approvals_pending,
      (select count(*)::int from pauli.incidents where organization_id=${orgId}::uuid and status <> 'resolved') open_incidents
  `)[0];

  const ownerBriefRows = await sql`
    select b.id,b.brief_hash,b.outcome,b.decisions,b.evidence,b.needs_you,b.working_now,b.created_at,
           s.coverage_status,s.as_of,s.provenance,s.source_hash
    from pauli.owner_briefs b
    join pauli.business_metric_snapshots s on s.id=b.snapshot_id
    where b.organization_id=${orgId}::uuid
    order by b.created_at desc
    limit 1
  `;
  const ownerBrief = ownerBriefRows[0] ?? {
    outcome: {
      coverage_status: "missing",
      revenue_cents: null,
      cost_cents: null,
      profit_cents: null,
      pod_published: 0,
      digital_sell_ready: 0,
      software_preview_ready: 0,
    },
    decisions: [{
      priority: 100,
      action: "reconcile_business_metrics",
      reason: "No source-qualified owner brief has been recorded yet. Financial results are unknown, not zero.",
      evidence: [],
    }],
    evidence: [],
    needs_you: [],
    working_now: [],
    coverage_status: "missing",
    as_of: null,
    provenance: [],
    source_hash: null,
  };

  const missions = await sql`select id,title,status,mission_type,priority,requested_outcome,created_at from pauli.missions where organization_id=${orgId}::uuid order by created_at desc limit 8`;
  const agents = await sql`select id,agent_key,name,role,specialty,status,world_location_key,last_heartbeat_at from pauli.agents where organization_id=${orgId}::uuid order by case when agent_key='pauli' then 0 else 1 end,name limit 24`;
  const approvals = await sql`select id,mission_id,action_class,risk_class,scope,max_spend_cents,status,expires_at,created_at from pauli.approvals where organization_id=${orgId}::uuid and status='pending' order by created_at limit 8`;
  const providers = await sql`select provider_key,name,kind,capabilities,health_status,last_healthcheck_at from pauli.runtime_providers order by kind,name`;
  const incidents = await sql`select id,severity,incident_type,title,summary,status,detected_at from pauli.incidents where organization_id=${orgId}::uuid and status <> 'resolved' order by detected_at desc limit 5`;
  return { ...metrics, owner_brief: ownerBrief, missions, agents, approvals, providers, incidents };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return json({ error: "POST only" }, 405);
  try {
    const userId = await getUserId(req);
    if (!userId) return json({ error: "unauthorized" }, 401);
    const body = await req.json().catch(() => ({}));
    const action = String(body?.action ?? "overview");
    const orgSlug = String(body?.org_slug ?? "paulis-place");
    const member = await membership(orgSlug, userId);
    if (!member) return json({ error: "forbidden" }, 403);

    if (action === "overview") return json(await overview(member.organization_id));

    if (action === "create_mission") {
      const input = body?.mission ?? {};
      const title = String(input.title ?? "").trim();
      const intent = String(input.intent ?? "").trim();
      const requestedOutcome = String(input.requested_outcome ?? "").trim();
      const language = ["en", "es-MX", "mixed"].includes(input.language) ? input.language : "en";
      const completion = ["IMPLEMENTED", "VERIFIED", "DEPLOYED", "HEALTHY", "OUTCOME_ACHIEVED", "BUSINESS_OUTCOME_MEASURED"].includes(input.required_completion_level)
        ? input.required_completion_level
        : "OUTCOME_ACHIEVED";
      const budget = Number(input.autonomous_budget_cents ?? 0);
      if (title.length < 3 || intent.length < 3 || requestedOutcome.length < 3) return json({ error: "title, intent and requested outcome are required" }, 400);
      if (!Number.isInteger(budget) || budget < 0 || budget > 2500) return json({ error: "autonomous budget must be 0..2500 cents" }, 400);
      const rows = await sql`
        insert into pauli.missions(organization_id,created_by,title,intent_original,requested_outcome,language,mission_type,autonomous_budget_cents,required_completion_level,status,policy_snapshot)
        values(${member.organization_id}::uuid,${userId}::uuid,${title},${intent},${requestedOutcome},${language},${input.mission_type ?? null},${budget},${completion},'INTENT',${sql.json({ approval_policy: 'pauli-constitution-v1', external_writes: 'human-gated' })})
        returning *
      `;
      const mission = rows[0];
      await sql`insert into pauli.mission_events(organization_id,mission_id,correlation_id,event_type,source,public_summary,payload) values(${member.organization_id}::uuid,${mission.id}::uuid,${mission.correlation_id}::uuid,'MISSION_CREATED','human',${`Mission created: ${title}`},${sql.json({ status: 'INTENT', language })})`;
      return json({ mission }, 201);
    }

    if (action === "decide_approval") {
      if (!["owner", "admin", "operator", "reviewer"].includes(member.role)) return json({ error: "insufficient role" }, 403);
      const approvalId = String(body?.approval_id ?? "");
      const decision = String(body?.decision ?? "");
      if (!["approve", "deny"].includes(decision)) return json({ error: "decision must be approve or deny" }, 400);
      const rows = await sql`
        update pauli.approvals set status=${decision === 'approve' ? 'approved' : 'denied'}, decided_by=${userId}::uuid, rationale=${String(body?.rationale ?? '')}, decided_at=now()
        where id=${approvalId}::uuid and organization_id=${member.organization_id}::uuid and status='pending'
        returning *
      `;
      if (!rows[0]) return json({ error: "approval not found or already decided" }, 404);
      return json({ approval: rows[0] });
    }

    return json({ error: "unknown action" }, 400);
  } catch (error) {
    console.error(error);
    return json({ error: "control-plane error" }, 500);
  }
});
