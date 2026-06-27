const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  dashboard: {
    getStats: () => fetchJSON<DashboardStats>('/api/dashboard/stats'),
    getRevenueChart: (days = 30) => fetchJSON<RevenueData[]>(`/api/dashboard/revenue-chart?days=${days}`),
    getNiches: () => fetchJSON<NicheData[]>('/api/dashboard/niches'),
  },
  products: {
    list: (params?: ProductFilters) => {
      const searchParams = new URLSearchParams();
      if (params?.platform) searchParams.set('platform', params.platform);
      if (params?.status) searchParams.set('status', params.status);
      if (params?.niche) searchParams.set('niche', params.niche);
      return fetchJSON<ProductListResponse>(`/api/products/?${searchParams}`);
    },
    get: (id: number) => fetchJSON<Product>(`/api/products/${id}`),
    getImage: (id: number) => fetchJSON<{ base64: string }>(`/api/products/${id}/image`),
  },
  approvals: {
    getQueue: () => fetchJSON<ApprovalQueue>('/api/approvals/queue'),
    process: (productIds: number[], action: 'approve' | 'reject' | 'publish') =>
      fetchJSON<{ results: ApprovalResult[] }>('/api/approvals/action', {
        method: 'POST',
        body: JSON.stringify({ product_ids: productIds, action }),
      }),
  },
  tasks: {
    list: (status?: string) => fetchJSON<Task[]>(`/api/tasks/${status ? `?status=${status}` : ''}`),
    summary: () => fetchJSON<TaskSummary>('/api/tasks/summary'),
    errors: () => fetchJSON<Task[]>('/api/tasks/recent-errors'),
  },
  triggers: {
    scanTrends: () => fetchJSON<{ status: string }>('/api/trigger/scan-trends', { method: 'POST' }),
    scoreTrends: () => fetchJSON<{ status: string }>('/api/trigger/score-trends', { method: 'POST' }),
    createProducts: () => fetchJSON<{ status: string }>('/api/trigger/create-products', { method: 'POST' }),
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
