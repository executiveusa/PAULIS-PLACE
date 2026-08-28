-- Phase 7: source-qualified owner intelligence snapshots.
-- No snapshot value is authoritative without explicit provenance/as-of metadata.

create table if not exists pauli.economic_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  provider text not null,
  external_ref text not null,
  kind text not null check (kind in ('revenue','cost','refund','fee','payout')),
  amount_cents bigint not null check (amount_cents >= 0),
  currency text not null default 'USD',
  product_ref text,
  source_ref text,
  evidence jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null,
  recorded_at timestamptz not null default now(),
  unique (organization_id,provider,external_ref,kind)
);

create index if not exists economic_events_org_time_idx
  on pauli.economic_events(organization_id, occurred_at desc);

create table if not exists pauli.business_metric_snapshots (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  snapshot_key text not null,
  as_of timestamptz not null,
  coverage_status text not null check (coverage_status in ('complete','partial','stale','missing')),
  metrics jsonb not null default '{}'::jsonb,
  provenance jsonb not null default '[]'::jsonb,
  source_hash text not null,
  created_at timestamptz not null default now(),
  unique (organization_id,snapshot_key,source_hash)
);

create index if not exists business_metric_snapshots_org_idx
  on pauli.business_metric_snapshots(organization_id, as_of desc);

create table if not exists pauli.owner_briefs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  snapshot_id uuid not null references pauli.business_metric_snapshots(id) on delete cascade,
  brief_hash text not null,
  outcome jsonb not null default '{}'::jsonb,
  decisions jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '[]'::jsonb,
  needs_you jsonb not null default '[]'::jsonb,
  working_now jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  unique (snapshot_id,brief_hash)
);

alter table pauli.economic_events enable row level security;
alter table pauli.business_metric_snapshots enable row level security;
alter table pauli.owner_briefs enable row level security;

drop policy if exists economic_events_member_read on pauli.economic_events;
create policy economic_events_member_read on pauli.economic_events
for select using (
  exists (select 1 from pauli.memberships m
    where m.organization_id=economic_events.organization_id
      and m.user_id=auth.uid() and m.status='active')
);

drop policy if exists business_metric_snapshots_member_read on pauli.business_metric_snapshots;
create policy business_metric_snapshots_member_read on pauli.business_metric_snapshots
for select using (
  exists (select 1 from pauli.memberships m
    where m.organization_id=business_metric_snapshots.organization_id
      and m.user_id=auth.uid() and m.status='active')
);

drop policy if exists owner_briefs_member_read on pauli.owner_briefs;
create policy owner_briefs_member_read on pauli.owner_briefs
for select using (
  exists (select 1 from pauli.memberships m
    where m.organization_id=owner_briefs.organization_id
      and m.user_id=auth.uid() and m.status='active')
);
