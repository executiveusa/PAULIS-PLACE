-- Phase 2: persistent worker leases and restart recovery.
-- Additive-only. Mission Control remains authoritative.

create table if not exists pauli.worker_leases (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  task_id uuid not null references pauli.mission_tasks(id) on delete cascade,
  worker_key text not null,
  lease_token uuid not null default gen_random_uuid(),
  status text not null default 'active' check (status in ('active','released','expired','recovered')),
  acquired_at timestamptz not null default now(),
  heartbeat_at timestamptz not null default now(),
  expires_at timestamptz not null,
  released_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  unique (task_id, worker_key, status)
);

create unique index if not exists worker_leases_one_active_per_task
  on pauli.worker_leases(task_id)
  where status='active';

create index if not exists worker_leases_expiry_idx
  on pauli.worker_leases(status, expires_at);

alter table pauli.worker_leases enable row level security;

drop policy if exists worker_leases_member_read on pauli.worker_leases;
create policy worker_leases_member_read on pauli.worker_leases
for select using (
  exists (
    select 1 from pauli.memberships m
    where m.organization_id = worker_leases.organization_id
      and m.user_id = auth.uid()
      and m.status='active'
  )
);
