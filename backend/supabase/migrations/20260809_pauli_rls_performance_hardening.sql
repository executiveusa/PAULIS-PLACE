-- Pauli-specific hardening after Supabase advisor review.
-- Avoid overlapping SELECT policies by replacing FOR ALL writer policies with
-- explicit INSERT/UPDATE/DELETE policies. Add covering FK indexes used by mission,
-- approval, runtime, evidence, world and treasury joins.

create index if not exists pauli_memberships_user_idx on pauli.memberships(user_id);
create index if not exists pauli_missions_created_by_idx on pauli.missions(created_by);
create index if not exists pauli_missions_parent_idx on pauli.missions(parent_mission_id);
create index if not exists pauli_missions_workflow_idx on pauli.missions(workflow_definition_id);
create index if not exists pauli_tasks_org_idx on pauli.mission_tasks(organization_id);
create index if not exists pauli_tasks_agent_idx on pauli.mission_tasks(assigned_agent_id);
create index if not exists pauli_events_task_idx on pauli.mission_events(task_id);
create index if not exists pauli_events_agent_idx on pauli.mission_events(agent_id);
create index if not exists pauli_approvals_mission_idx on pauli.approvals(mission_id);
create index if not exists pauli_approvals_task_idx on pauli.approvals(task_id);
create index if not exists pauli_approvals_agent_idx on pauli.approvals(requested_by_agent_id);
create index if not exists pauli_approvals_decider_idx on pauli.approvals(decided_by);
create index if not exists pauli_runtime_org_idx on pauli.runtime_runs(organization_id);
create index if not exists pauli_runtime_mission_idx on pauli.runtime_runs(mission_id);
create index if not exists pauli_runtime_agent_idx on pauli.runtime_runs(agent_id);
create index if not exists pauli_runtime_provider_idx on pauli.runtime_runs(provider_id);
create index if not exists pauli_compute_org_idx on pauli.compute_sessions(organization_id);
create index if not exists pauli_compute_mission_idx on pauli.compute_sessions(mission_id);
create index if not exists pauli_compute_agent_idx on pauli.compute_sessions(agent_id);
create index if not exists pauli_memory_org_idx on pauli.memory_entries(organization_id);
create index if not exists pauli_memory_mission_idx on pauli.memory_entries(mission_id);
create index if not exists pauli_checkpoints_org_idx on pauli.checkpoints(organization_id);
create index if not exists pauli_checkpoints_mission_idx on pauli.checkpoints(mission_id);
create index if not exists pauli_checkpoints_task_idx on pauli.checkpoints(task_id);
create index if not exists pauli_evidence_org_idx on pauli.evidence_receipts(organization_id);
create index if not exists pauli_evidence_task_idx on pauli.evidence_receipts(task_id);
create index if not exists pauli_evidence_runtime_idx on pauli.evidence_receipts(runtime_run_id);
create index if not exists pauli_world_presence_mission_idx on pauli.world_presence(mission_id);
create index if not exists pauli_world_presence_location_idx on pauli.world_presence(location_id);
create index if not exists pauli_experiments_org_idx on pauli.experiments(organization_id);
create index if not exists pauli_experiments_mission_idx on pauli.experiments(mission_id);
create index if not exists pauli_treasury_mission_idx on pauli.treasury_entries(mission_id);
create index if not exists pauli_treasury_experiment_idx on pauli.treasury_entries(experiment_id);
create index if not exists pauli_documents_org_idx on pauli.documents(organization_id);
create index if not exists pauli_documents_mission_idx on pauli.documents(mission_id);
create index if not exists pauli_audit_org_idx on pauli.audit_log(organization_id);
create index if not exists pauli_audit_user_idx on pauli.audit_log(actor_user_id);
create index if not exists pauli_audit_agent_idx on pauli.audit_log(actor_agent_id);

-- Drop writer policies that also apply to SELECT.
drop policy if exists memberships_admin_write on pauli.memberships;
drop policy if exists agents_operator_write on pauli.agents;
drop policy if exists workflows_admin_write on pauli.workflow_definitions;
drop policy if exists approvals_reviewer_write on pauli.approvals;
drop policy if exists world_locations_write on pauli.world_locations;

do $$
declare t text;
begin
  foreach t in array array[
    'missions','mission_tasks','mission_events','runtime_runs','compute_sessions','memory_entries',
    'checkpoints','evidence_receipts','integration_connections','world_presence','experiments',
    'treasury_entries','documents'
  ] loop
    execute format('drop policy if exists %I on pauli.%I', t || '_operator_write', t);
  end loop;
end $$;

-- Membership writes.
create policy memberships_admin_insert on pauli.memberships for insert to authenticated
with check ((select pauli_private.has_org_role(organization_id,array['owner','admin'])));
create policy memberships_admin_update on pauli.memberships for update to authenticated
using ((select pauli_private.has_org_role(organization_id,array['owner','admin'])))
with check ((select pauli_private.has_org_role(organization_id,array['owner','admin'])));
create policy memberships_admin_delete on pauli.memberships for delete to authenticated
using ((select pauli_private.has_org_role(organization_id,array['owner','admin'])));

-- Agent writes.
create policy agents_operator_insert on pauli.agents for insert to authenticated
with check ((select pauli_private.has_org_role(organization_id,array['owner','admin','operator'])));
create policy agents_operator_update on pauli.agents for update to authenticated
using ((select pauli_private.has_org_role(organization_id,array['owner','admin','operator'])))
with check ((select pauli_private.has_org_role(organization_id,array['owner','admin','operator'])));
create policy agents_operator_delete on pauli.agents for delete to authenticated
using ((select pauli_private.has_org_role(organization_id,array['owner','admin'])));

-- Workflow definition writes.
create policy workflows_admin_insert on pauli.workflow_definitions for insert to authenticated
with check (organization_id is not null and (select pauli_private.has_org_role(organization_id,array['owner','admin','operator'])));
create policy workflows_admin_update on pauli.workflow_definitions for update to authenticated
using (organization_id is not null and (select pauli_private.has_org_role(organization_id,array['owner','admin','operator'])))
with check (organization_id is not null and (select pauli_private.has_org_role(organization_id,array['owner','admin','operator'])));
create policy workflows_admin_delete on pauli.workflow_definitions for delete to authenticated
using (organization_id is not null and (select pauli_private.has_org_role(organization_id,array['owner','admin'])));

-- Standard operational writes, separate from the member SELECT policy.
do $$
declare t text;
begin
  foreach t in array array[
    'missions','mission_tasks','mission_events','runtime_runs','compute_sessions','memory_entries',
    'checkpoints','evidence_receipts','integration_connections','world_presence','experiments',
    'treasury_entries','documents'
  ] loop
    execute format('create policy %I on pauli.%I for insert to authenticated with check ((select pauli_private.has_org_role(organization_id,array[''owner'',''admin'',''operator''])))', t || '_operator_insert', t);
    execute format('create policy %I on pauli.%I for update to authenticated using ((select pauli_private.has_org_role(organization_id,array[''owner'',''admin'',''operator'']))) with check ((select pauli_private.has_org_role(organization_id,array[''owner'',''admin'',''operator''])))', t || '_operator_update', t);
    execute format('create policy %I on pauli.%I for delete to authenticated using ((select pauli_private.has_org_role(organization_id,array[''owner'',''admin''])))', t || '_admin_delete', t);
  end loop;
end $$;

-- Approval decisions can be written by reviewers/admins but not ordinary operators.
create policy approvals_reviewer_insert on pauli.approvals for insert to authenticated
with check ((select pauli_private.has_org_role(organization_id,array['owner','admin','reviewer'])));
create policy approvals_reviewer_update on pauli.approvals for update to authenticated
using ((select pauli_private.has_org_role(organization_id,array['owner','admin','reviewer'])))
with check ((select pauli_private.has_org_role(organization_id,array['owner','admin','reviewer'])));
create policy approvals_admin_delete on pauli.approvals for delete to authenticated
using ((select pauli_private.has_org_role(organization_id,array['owner','admin'])));

-- World-location writes.
create policy world_locations_insert on pauli.world_locations for insert to authenticated
with check (organization_id is not null and (select pauli_private.has_org_role(organization_id,array['owner','admin','operator'])));
create policy world_locations_update on pauli.world_locations for update to authenticated
using (organization_id is not null and (select pauli_private.has_org_role(organization_id,array['owner','admin','operator'])))
with check (organization_id is not null and (select pauli_private.has_org_role(organization_id,array['owner','admin','operator'])));
create policy world_locations_delete on pauli.world_locations for delete to authenticated
using (organization_id is not null and (select pauli_private.has_org_role(organization_id,array['owner','admin'])));
