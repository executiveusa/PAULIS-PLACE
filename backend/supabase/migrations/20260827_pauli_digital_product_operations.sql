-- Phase 6: governed digital-product creation/package ledger.
-- Designer creates artifacts; this ledger owns provenance, deterministic package
-- identity, quality/evidence gates, distribution drafts, and publish approval.

create table if not exists pauli.digital_product_operations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid not null references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  idempotency_key text not null,
  input_hash text not null,
  product_key text not null,
  product_type text not null,
  status text not null default 'started' check (status in (
    'started','brief_ready','research_ready','artifact_ready','package_validating',
    'repairing','quality_verified','listing_draft_ready','waiting_publish_approval',
    'published','blocked','failed'
  )),
  brief jsonb not null default '{}'::jsonb,
  research_provenance jsonb not null default '[]'::jsonb,
  artifact_manifest jsonb not null default '{}'::jsonb,
  artifact_sha256 text,
  package_manifest jsonb not null default '{}'::jsonb,
  package_sha256 text,
  quality_receipt jsonb not null default '{}'::jsonb,
  critic_receipt jsonb not null default '{}'::jsonb,
  guardian_receipt jsonb not null default '{}'::jsonb,
  distribution_provider text,
  distribution_draft_id text,
  distribution_ref text,
  publish_approval_id uuid references pauli.approvals(id) on delete set null,
  evidence jsonb not null default '[]'::jsonb,
  error_class text,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (organization_id, idempotency_key),
  unique (organization_id, product_key, package_sha256)
);

create index if not exists digital_product_operations_mission_idx
  on pauli.digital_product_operations(organization_id, mission_id, created_at desc);

create table if not exists pauli.digital_product_receipts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  operation_id uuid not null references pauli.digital_product_operations(id) on delete cascade,
  stage text not null check (stage in (
    'brief','research','artifact','package','quality','critic','repair','guardian','listing_draft','publish'
  )),
  status text not null check (status in ('passed','failed','blocked','recorded')),
  sha256 text not null,
  summary text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (operation_id,stage,sha256)
);

create index if not exists digital_product_receipts_operation_idx
  on pauli.digital_product_receipts(operation_id, created_at);

alter table pauli.digital_product_operations enable row level security;
alter table pauli.digital_product_receipts enable row level security;

drop policy if exists digital_product_operations_member_read on pauli.digital_product_operations;
create policy digital_product_operations_member_read on pauli.digital_product_operations
for select using (
  exists (
    select 1 from pauli.memberships m
    where m.organization_id=digital_product_operations.organization_id
      and m.user_id=auth.uid() and m.status='active'
  )
);

drop policy if exists digital_product_receipts_member_read on pauli.digital_product_receipts;
create policy digital_product_receipts_member_read on pauli.digital_product_receipts
for select using (
  exists (
    select 1 from pauli.memberships m
    where m.organization_id=digital_product_receipts.organization_id
      and m.user_id=auth.uid() and m.status='active'
  )
);
