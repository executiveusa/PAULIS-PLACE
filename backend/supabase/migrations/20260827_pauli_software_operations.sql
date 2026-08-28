-- Phase 5: governed software-factory operation and immutable stage receipts.
-- Additive-only. Autonomous workers may build previews on mission-bound branches;
-- production deployment remains a separately approved capability.

create table if not exists pauli.software_operations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid not null references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  idempotency_key text not null,
  input_hash text not null,
  repository_full_name text not null,
  base_ref text not null default 'main',
  base_sha text,
  branch_ref text,
  commit_sha text,
  workspace_ref text,
  status text not null default 'started' check (status in (
    'started','spec_ready','workspace_ready','branch_ready','building',
    'tests_failed','repairing','verified','preview_deploying','preview_ready',
    'waiting_production_approval','production_deploying','production_deployed',
    'blocked','failed'
  )),
  spec jsonb not null default '{}'::jsonb,
  build_receipt jsonb not null default '{}'::jsonb,
  test_receipt jsonb not null default '{}'::jsonb,
  critic_receipt jsonb not null default '{}'::jsonb,
  guardian_receipt jsonb not null default '{}'::jsonb,
  preview_provider text,
  preview_deployment_id text,
  preview_url text,
  production_approval_id uuid references pauli.approvals(id) on delete set null,
  evidence jsonb not null default '[]'::jsonb,
  error_class text,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (organization_id, idempotency_key)
);

create index if not exists software_operations_mission_idx
  on pauli.software_operations(organization_id, mission_id, created_at desc);
create index if not exists software_operations_branch_idx
  on pauli.software_operations(repository_full_name, branch_ref);

create table if not exists pauli.software_receipts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  operation_id uuid not null references pauli.software_operations(id) on delete cascade,
  stage text not null check (stage in (
    'spec','workspace','git_branch','build','test','critic','repair','preview','guardian','production'
  )),
  status text not null check (status in ('passed','failed','blocked','recorded')),
  sha256 text not null,
  summary text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (operation_id, stage, sha256)
);

create index if not exists software_receipts_operation_idx
  on pauli.software_receipts(operation_id, created_at);

alter table pauli.software_operations enable row level security;
alter table pauli.software_receipts enable row level security;

drop policy if exists software_operations_member_read on pauli.software_operations;
create policy software_operations_member_read on pauli.software_operations
for select using (
  exists (
    select 1 from pauli.memberships m
    where m.organization_id = software_operations.organization_id
      and m.user_id = auth.uid()
      and m.status='active'
  )
);

drop policy if exists software_receipts_member_read on pauli.software_receipts;
create policy software_receipts_member_read on pauli.software_receipts
for select using (
  exists (
    select 1 from pauli.memberships m
    where m.organization_id = software_receipts.organization_id
      and m.user_id = auth.uid()
      and m.status='active'
  )
);
