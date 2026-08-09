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
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();
    setDemoMode(false);
    return data as T;
  } catch (e) {
    setDemoMode(true);
    throw e;
  }
}

// Endpoints below each fall back to the embedded demo engine when the real
// backend is unreachable, so the app is never an empty skeleton.
const D = demo as any;

function withDemo<T>(real: () => Promise<T>, demoFn: () => T | Promise<T>): Promise<T> {
  return (async () => {
    try { return await real(); } catch { setDemoMode(true); return (await demoFn()) as T; }
  })();
}

export const api = {
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
