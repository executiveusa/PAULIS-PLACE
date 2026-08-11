export type PauliverseNodeType =
  | 'REPOSITORY'
  | 'PROJECT'
  | 'BUSINESS'
  | 'CAPABILITY'
  | 'SKILL'
  | 'AGENT'
  | 'PERSON'
  | 'IDEA'
  | 'IP_ASSET'
  | 'CHARACTER'
  | 'STORY_CANON'
  | 'PRODUCT'
  | 'OPPORTUNITY'
  | 'EXPERIMENT'
  | 'DECISION'
  | 'EVIDENCE'
  | 'CUSTOMER'
  | 'PARTNER'
  | 'CAUSE'
  | 'DEPLOYMENT'
  | string;

export interface PauliverseNode {
  id: string;
  type: PauliverseNodeType;
  name: string;
  authority?: string;
  status?: string;
  disposition?: string;
  district?: string;
  repo?: string | null;
  deployment_url?: string | null;
  health?: string | null;
  summary?: string | null;
  active_missions?: string[];
  financial_signals?: string[];
  owner_approvals_required?: string[];
  evidence_refs?: string[];
  provenance?: {
    source_type?: string;
    source_ref?: string;
    observed_at?: string;
    confidence?: number;
  };
}

export interface PauliverseEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  active?: boolean;
  mission_id?: string | null;
  provenance?: {
    source_type?: string;
    source_ref?: string;
    observed_at?: string;
    confidence?: number;
  };
}

export interface PauliverseSnapshot {
  schema_version: number;
  generated_at: string;
  source: string;
  nodes: PauliverseNode[];
  edges: PauliverseEdge[];
}

export async function fetchPauliverseSnapshot(): Promise<PauliverseSnapshot> {
  const response = await fetch('/api/pauliverse/snapshot', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Pauliverse snapshot unavailable (${response.status})`);
  }
  const data = await response.json();
  if (!data || data.schema_version !== 1 || !Array.isArray(data.nodes) || !Array.isArray(data.edges)) {
    throw new Error('Pauliverse snapshot failed schema validation');
  }
  return data as PauliverseSnapshot;
}
