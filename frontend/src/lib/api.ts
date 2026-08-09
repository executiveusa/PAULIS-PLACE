import { demo } from './demo';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export let isDemoMode = false;
export function setDemoMode(v: boolean) { isDemoMode = v; }

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) {
      let detail = `API error: ${res.status}`;
      try {
        const body = await res.json();
        if (body?.detail) detail = String(body.detail);
      } catch {}
      throw new Error(detail);
    }
    const data = await res.json();
    setDemoMode(false);
    return data as T;
  } catch (e) {
    throw e;
  }
}

// Legacy factory rooms still support explicit demo fallback. Mission Control,
// agents, integrations and other operational surfaces never fabricate state.
const D = demo as any;

function withDemo<T>(real: () => Promise<T>, demoFn: () => T | Promise<T>): Promise<T> {
  return (async () => {
    try { return await real(); } catch { setDemoMode(true); return (await demoFn()) as T; }
  })();
}

export const api = {
  controlPlane: {
    status: () => fetchJSON<ControlPlaneStatus>('/api/control-plane/status'),
    agents: (organizationSlug = 'paulis-place') =>
      fetchJSON<AgentListResponse>(`/api/control-plane/agents?organization_slug=${encodeURIComponent(organizationSlug)}`),
    missions: (organizationSlug = 'paulis-place', limit = 30) =>
      fetchJSON<MissionListResponse>(`/api/control-plane/missions?organization_slug=${encodeURIComponent(organizationSlug)}&limit=${limit}`),
    createMission: (payload: MissionCreateRequest) =>
      fetchJSON<MissionCreateResponse>('/api/control-plane/missions', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    agentForgeStatus: () => fetchJSON<AgentForgeStatus>('/api/control-plane/providers/agentforge'),
  },
  dashboard: {
    getStats: () => withDemo(() => fetchJSON<DashboardStats>('/api/dashboard/stats'), () => D.dashboardStats()),
    getRevenueChart: (days = 30) => withDemo(() => fetchJSON<RevenueData[]>(`/api/dashboard/revenue-chart?days=${days}`), () => D.revenueChart(days)),
    getNiches: () => withDemo(() => fetchJSON<NicheData[]>('/api/dashboard/niches'), () => D.niches()),
  },
  products: {
    list: (params?: ProductFilters) => {
      const searchParams = new URLSearchParams();
      if (params?.platform) searchParams.set('platform', params.platform);
      if (params?.status) searchParams.set('status', params.status);
      if (params?.niche) searchParams.set('niche', params.niche);
      return withDemo(() => fetchJSON<ProductListResponse>(`/api/products/?${searchParams}`), () => D.products());
    },
    get: (id: number) => withDemo(() => fetchJSON<Product>(`/api/products/${id}`), () => D.products().then((r: any) => r.items.find((p: any) => p.id === id) || r.items[0])),
    getImage: (id: number) => withDemo(() => fetchJSON<{ base64: string }>(`/api/products/${id}/image`), () => ({ base64: '' })),
  },
  approvals: {
    getQueue: () => withDemo(() => fetchJSON<ApprovalQueue>('/api/approvals/queue'), () => D.approvalQueue()),
    process: (productIds: number[], action: 'approve' | 'reject' | 'publish') =>
      withDemo(() => fetchJSON<{ results: ApprovalResult[] }>('/api/approvals/action', {
        method: 'POST',
        body: JSON.stringify({ product_ids: productIds, action }),
      }), () => ({ results: productIds.map((id) => ({ id, status: action })) })),
  },
  tasks: {
    list: (status?: string) => withDemo(() => fetchJSON<Task[]>(`/api/tasks/${status ? `?status=${status}` : ''}`), () => D.tasks()),
    summary: () => withDemo(() => fetchJSON<TaskSummary>('/api/tasks/summary'), () => D.taskSummary()),
    errors: () => withDemo(() => fetchJSON<Task[]>(`/api/tasks/recent-errors`), () => D.tasks().filter((t: any) => t.status === 'failed')),
  },
  integrations: {
    composioStatus: () => fetchJSON<ComposioStatus>('/api/integrations/composio/status'),
    createReadSession: (tenantId: string, actorId: string, toolkits: string[]) =>
      fetchJSON<ComposioSession>('/api/integrations/composio/sessions/read', {
        method: 'POST',
        body: JSON.stringify({ tenant_id: tenantId, actor_id: actorId, toolkits }),
      }),
    connectToolkit: (sessionId: string, toolkit: string, callbackUrl?: string) =>
      fetchJSON<ComposioConnection>(`/api/integrations/composio/sessions/${sessionId}/connect`, {
        method: 'POST',
        body: JSON.stringify({ toolkit, callback_url: callbackUrl }),
      }),
  },
  triggers: {
    scanTrends: () => withDemo(() => fetchJSON<{ status: string }>('/api/trigger/scan-trends', { method: 'POST' }), () => ({ status: 'queued' })),
    scoreTrends: () => withDemo(() => fetchJSON<{ status: string }>('/api/trigger/score-trends', { method: 'POST' }), () => ({ status: 'queued' })),
    createProducts: () => withDemo(() => fetchJSON<{ status: string }>('/api/trigger/create-products', { method: 'POST' }), () => ({ status: 'queued' })),
  },
};

export interface ProviderHealth {
  provider?: string;
  configured?: boolean;
  installed?: boolean;
  status: string;
  capabilities?: string[] | readonly string[];
  detail?: string | null;
  [key: string]: unknown;
}

export interface ControlPlaneStatus {
  product: string;
  status: string;
  timestamp: string;
  database: { schema: string; ready: boolean; error?: string };
  providers: { agentforge: ProviderHealth; composio: ProviderHealth };
  counts: { organizations: number; agents: number; missions: number; approvals_pending: number };
}

export interface PauliAgent {
  id: string;
  agent_key: string;
  name: string;
  role: string;
  specialty?: string | null;
  status: string;
  world_location_key?: string | null;
  last_heartbeat_at?: string | null;
  skill_manifest?: unknown[];
  model_policy?: Record<string, unknown>;
  runtime_policy?: Record<string, unknown>;
}

export interface AgentListResponse {
  organization_slug: string;
  agents: PauliAgent[];
  status: string;
}

export interface Mission {
  id: string;
  title: string;
  intent_original: string;
  requested_outcome: string;
  language: 'en' | 'es-MX' | 'mixed';
  mission_type?: string | null;
  required_completion_level: string;
  status: string;
  priority: number;
  autonomous_budget_cents: number;
  spent_cents: number;
  attempt_count: number;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface MissionListResponse {
  organization_slug: string;
  missions: Mission[];
  status: string;
}

export interface MissionCreateRequest {
  title: string;
  intent: string;
  requested_outcome: string;
  language?: 'en' | 'es-MX' | 'mixed';
  mission_type?: string;
  required_completion_level?: string;
  autonomous_budget_cents?: number;
  organization_slug?: string;
}

export interface MissionCreateResponse {
  mission_id: string;
  correlation_id: string;
  status: string;
  title: string;
  requested_outcome: string;
}

export interface AgentForgeStatus extends ProviderHealth {
  python?: string;
  project_dir?: string;
}

export interface DashboardStats {
  products: { total: number; published: number; pending_approval: number; drafts: number };
  revenue: { total: number; last_7_days: number; total_sales: number; by_platform: Record<string, { revenue: number; count: number }> };
  trends: { hot: number; breakout: number };
  tasks: { running: number; failed: number };
}

export interface Product {
  id: number; external_id: string; platform: string; product_type: string;
  title: string; description: string; tags: string[]; niche: string;
  price: number; status: string; views: number; sales: number; revenue: number;
  created_at: string; research_data?: any;
}

export interface Task { id: number; task_type: string; status: string; ai_cost: number; created_at: string; }
export interface ApprovalQueue { pending: Product[]; ready_to_publish: Product[]; }
export interface ApprovalResult { id: number; status: string; message?: string; }
export interface ProductFilters { platform?: string; status?: string; niche?: string; }
export interface ProductListResponse { total: number; items: Product[]; }
export interface RevenueData { date: string; products_created: number; revenue: number; }
export interface NicheData { id: number; niche: string; avg_price: number; updated_at: string; }
export interface TaskSummary { [taskType: string]: { pending?: number; running?: number; completed?: number; failed?: number; }; }

export interface Trend {
  id: number; keyword: string; niche: string; interest_score: number;
  change_7d: number; change_30d: number; opportunity_score: number;
  competition_level: string; product_ideas: ProductIdea[];
  is_breakout: boolean; is_seasonal: boolean; is_evergreen: boolean;
  products_created: number; last_scanned: string;
}

export interface ProductIdea {
  type: string; angle: string; prompt_direction: string;
}

export interface ComposioStatus {
  provider: string;
  configured: boolean;
  status: 'ready' | 'waiting_for_credentials';
  capabilities: string[];
}
export interface ComposioSession {
  session_id: string;
  pauli_entity_id: string;
  access_mode: 'read' | 'action';
  toolkits: string[];
  mcp_url?: string;
  warnings?: Array<Record<string, unknown>>;
}
export interface ComposioConnection {
  redirect_url?: string;
  link_url?: string;
  connection_status?: string;
  [key: string]: unknown;
}
