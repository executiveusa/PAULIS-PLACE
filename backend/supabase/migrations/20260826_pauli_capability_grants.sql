-- Phase 3: capability grants, revocation and execution-policy receipts.
-- Additive-only. Mission Control remains authoritative.

create table if not exists pauli.capability_grants (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  agent_id uuid references pauli.agents(id) on delete cascade,
  capability_key text not null,
  scope jsonb not null default '{}'::jsonb,
  risk_class text not null default 'SAFE' check (risk_class in ('SAFE','CAUTION','DANGEROUS','CRITICAL')),
  max_spend_cents integer,
  status text not null default 'active' check (status in ('active','revoked','expired')),
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists capability_grants_lookup_idx
  on pauli.capability_grants(organization_id, agent_id, capability_key, status);

create table if not exists pauli.capability_decisions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid not null references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  agent_id uuid references pauli.agents(id) on delete set null,
  capability_key text not null,
  decision text not null check (decision in ('allow','deny','approval_required')),
  risk_class text not null check (risk_class in ('SAFE','CAUTION','DANGEROUS','CRITICAL')),
  reason text not null,
  grant_id uuid references pauli.capability_grants(id) on delete set null,
  approval_id uuid references pauli.approvals(id) on delete set null,
  estimated_spend_cents integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table pauli.capability_grants enable row level security;
alter table pauli.capability_decisions enable row level security;

drop policy if exists capability_grants_member_read on pauli.capability_grants;
create policy capability_grants_member_read on pauli.capability_grants
for select using (
  exists (
    select 1 from pauli.memberships m
    where m.organization_id = capability_grants.organization_id
      and m.user_id = auth.uid()
      and m.status='active'
  )
);

drop policy if exists capability_decisions_member_read on pauli.capability_decisions;
create policy capability_decisions_member_read on pauli.capability_decisions
for select using (
  exists (
    select 1 from pauli.memberships m
    where m.organization_id = capability_decisions.organization_id
      and m.user_id = auth.uid()
      and m.status='active'
  )
);
