-- Phase 4: replay-safe POD commerce operation ledger.
-- Additive-only. External product/listing IDs are persisted before later stages.

create table if not exists pauli.commerce_operations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  source_product_id bigint,
  operation_type text not null check (operation_type in ('pod_draft','pod_publish')),
  idempotency_key text not null,
  status text not null default 'started' check (status in ('started','printify_created','etsy_draft_created','draft_ready','waiting_approval','publishing','published','blocked','failed')),
  input_hash text not null,
  printify_product_id text,
  etsy_listing_id bigint,
  etsy_listing_image_id bigint,
  approval_id uuid references pauli.approvals(id) on delete set null,
  evidence jsonb not null default '[]'::jsonb,
  error_class text,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (organization_id, idempotency_key)
);

create index if not exists commerce_operations_mission_idx
  on pauli.commerce_operations(organization_id, mission_id, created_at desc);

create index if not exists commerce_operations_product_idx
  on pauli.commerce_operations(source_product_id, created_at desc);

alter table pauli.commerce_operations enable row level security;

drop policy if exists commerce_operations_member_read on pauli.commerce_operations;
create policy commerce_operations_member_read on pauli.commerce_operations
for select using (
  exists (
    select 1 from pauli.memberships m
    where m.organization_id = commerce_operations.organization_id
      and m.user_id = auth.uid()
      and m.status='active'
  )
);
