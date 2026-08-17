-- Idempotent Pauli's Place bootstrap data.
-- Safe to re-run after the control-plane migrations.

with org as (
  insert into pauli.organizations (slug,name,preferred_language,status,metadata)
  values ('paulis-place','Pauli''s Place','en','active',jsonb_build_object('spanish_variant','es-MX','canonical',true))
  on conflict (slug) do update set name=excluded.name, updated_at=now()
  returning id
), org_id as (
  select id from org union all select id from pauli.organizations where slug='paulis-place' limit 1
)
insert into pauli.agents (
  organization_id,agent_key,name,role,specialty,identity,heart,soul,persona_static,persona_retrieval,
  skill_manifest,runtime_policy,model_policy,compute_policy,status,world_location_key
)
select id,'pauli','Pauli','Executive Agent',
  'Turns plain-language intent into staffed, governed missions and verified outcomes',
  jsonb_build_object('avatar','canonical-pauli','type','cartoon-noir-sasquatch','language_order',jsonb_build_array('en','es-MX')),
  jsonb_build_object('values',jsonb_build_array('help people','tell the truth','protect the client','finish the job')),
  jsonb_build_object('tone','calm, resourceful, funny when appropriate','north_star','human intent -> verified outcome'),
  jsonb_build_object('name','Pauli','goal','Make the technical disappear for the human'),
  jsonb_build_object('expertise',jsonb_build_array('mission routing','team assembly','business operations','agent coordination'),
    'principles',jsonb_build_array('evidence over claims','signals over noise','ask only for consequential authority')),
  jsonb_build_array('mission-control','team-assembly','approval-routing','gauntlet','composio','voice'),
  jsonb_build_object('preferred',jsonb_build_array('agentforge','hermes','pi','openhands','open-interpreter'),'resume',true),
  jsonb_build_object('auto_route',true,'frontier_requires_approval',true,'prefer_local_when_adequate',true),
  jsonb_build_object('logical_workstation',true,'provider_selection','best-adequate-by-capability-cost-privacy','orgo_fallback',true),
  'idle','paulis-place'
from org_id
on conflict (organization_id,agent_key) do update set
  name=excluded.name, role=excluded.role, specialty=excluded.specialty, identity=excluded.identity,
  heart=excluded.heart, soul=excluded.soul, persona_static=excluded.persona_static,
  persona_retrieval=excluded.persona_retrieval, skill_manifest=excluded.skill_manifest,
  runtime_policy=excluded.runtime_policy, model_policy=excluded.model_policy,
  compute_policy=excluded.compute_policy, updated_at=now();

insert into pauli.runtime_providers (provider_key,name,kind,capabilities,health_status,cost_profile,metadata)
values
 ('agentforge','AgentForge','agent_runtime',jsonb_build_object('cogs',true,'personas',true,'memory',true,'branching',true,'model_agnostic',true),'unconfigured','{}'::jsonb,jsonb_build_object('source_repo','executiveusa/pauli-Agent-Forge')),
 ('composio','Composio','integration',jsonb_build_object('hosted_mcp',true,'oauth',true,'tool_discovery',true,'tenant_sessions',true),'unconfigured','{}'::jsonb,'{}'::jsonb),
 ('hostinger-coolify','Hostinger + Coolify','compute',jsonb_build_object('linux',true,'docker',true,'owned_capacity',true),'unknown','{}'::jsonb,'{}'::jsonb),
 ('runpod','RunPod','compute',jsonb_build_object('gpu',true,'ephemeral',true),'unconfigured','{}'::jsonb,'{}'::jsonb),
 ('orgo','Orgo','compute',jsonb_build_object('gui',true,'desktop',true,'fallback',true),'unconfigured','{}'::jsonb,'{}'::jsonb)
on conflict (provider_key) do update set capabilities=excluded.capabilities, metadata=excluded.metadata, updated_at=now();

with org as (select id from pauli.organizations where slug='paulis-place')
insert into pauli.world_locations (organization_id,location_key,name,visibility,scene_ref,metadata)
select org.id,v.location_key,v.name,v.visibility,v.scene_ref,v.metadata
from org cross join (values
 ('paulis-place','Pauli''s Place','tenant','scene://paulis-place',jsonb_build_object('purpose','executive headquarters')),
 ('maxs','Max''s','tenant','scene://maxs',jsonb_build_object('purpose','client workspace')),
 ('factory','The Factory','tenant','scene://factory',jsonb_build_object('purpose','software and digital products')),
 ('studio','The Studio','tenant','scene://studio',jsonb_build_object('purpose','media and storytelling')),
 ('garage','The Garage','tenant','scene://garage',jsonb_build_object('purpose','compute and infrastructure')),
 ('library','The Library','tenant','scene://library',jsonb_build_object('purpose','research')),
 ('bank','The Bank','private','scene://bank',jsonb_build_object('purpose','treasury and economics')),
 ('grant-office','Grant Office','tenant','scene://grant-office',jsonb_build_object('purpose','grants and sponsorships')),
 ('hiring-hall','Hiring Hall','member','scene://hiring-hall',jsonb_build_object('purpose','agents for hire')),
 ('war-room','War Room','private','scene://war-room',jsonb_build_object('purpose','incidents and critical decisions'))
) as v(location_key,name,visibility,scene_ref,metadata)
on conflict (organization_id,location_key) do update set
  name=excluded.name, visibility=excluded.visibility, scene_ref=excluded.scene_ref, metadata=excluded.metadata;
