const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://cyxdevcjycmffhmwxojh.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || 'sb_publishable_PoqI-3PsCqewtJWJ0Z73Ag_5hIE0oKI';
const CONTROL_URL = `${SUPABASE_URL}/functions/v1/pauli-control`;
const SESSION_KEY = 'pauli.auth.session';

export interface PauliSession {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
  expires_at?: number;
  token_type?: string;
  user?: { id: string; email?: string };
}

export interface PauliAgentSummary {
  id: string;
  agent_key: string;
  name: string;
  role: string;
  specialty?: string;
  status: string;
  world_location_key?: string;
  last_heartbeat_at?: string;
}

export interface PauliMissionSummary {
  id: string;
  title: string;
  status: string;
  mission_type?: string;
  priority: number;
  requested_outcome: string;
  created_at: string;
}

export interface PauliApprovalSummary {
  id: string;
  mission_id?: string;
  action_class: string;
  risk_class: string;
  scope: Record<string, unknown>;
  max_spend_cents?: number;
  status: string;
  expires_at?: string;
  created_at: string;
}

export interface PauliProviderSummary {
  provider_key: string;
  name: string;
  kind: string;
  capabilities: unknown;
  health_status: string;
  last_healthcheck_at?: string;
}

export interface PauliIncidentSummary {
  id: string;
  severity: string;
  incident_type: string;
  title: string;
  summary: string;
  status: string;
  detected_at: string;
}

export interface PauliOverview {
  active_missions: number;
  agents_working: number;
  approvals_pending: number;
  open_incidents: number;
  revenue_today_cents: number | string;
  spend_today_cents: number | string;
  missions: PauliMissionSummary[];
  agents: PauliAgentSummary[];
  approvals: PauliApprovalSummary[];
  providers: PauliProviderSummary[];
  incidents: PauliIncidentSummary[];
}

function browser(): boolean {
  return typeof window !== 'undefined';
}

export function getSession(): PauliSession | null {
  if (!browser()) return null;
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const session = JSON.parse(raw) as PauliSession;
    if (!session.access_token) return null;
    return session;
  } catch {
    return null;
  }
}

export function storeSession(session: PauliSession): void {
  if (!browser()) return;
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  if (!browser()) return;
  window.localStorage.removeItem(SESSION_KEY);
}

export function captureMagicLinkSession(): PauliSession | null {
  if (!browser() || !window.location.hash) return getSession();
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  const accessToken = params.get('access_token');
  if (!accessToken) return getSession();
  const expiresIn = Number(params.get('expires_in') || '3600');
  const session: PauliSession = {
    access_token: accessToken,
    refresh_token: params.get('refresh_token') || undefined,
    expires_in: expiresIn,
    expires_at: Math.floor(Date.now() / 1000) + expiresIn,
    token_type: params.get('token_type') || 'bearer',
  };
  storeSession(session);
  window.history.replaceState({}, document.title, `${window.location.pathname}${window.location.search}`);
  return session;
}

export async function requestMagicLink(email: string): Promise<void> {
  const redirectTo = browser() ? `${window.location.origin}/` : undefined;
  const res = await fetch(`${SUPABASE_URL}/auth/v1/otp`, {
    method: 'POST',
    headers: {
      apikey: SUPABASE_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, options: { emailRedirectTo: redirectTo } }),
  });
  if (!res.ok) throw new Error(`Authentication request failed (${res.status})`);
}

export async function signOut(): Promise<void> {
  const session = getSession();
  if (session?.access_token) {
    await fetch(`${SUPABASE_URL}/auth/v1/logout`, {
      method: 'POST',
      headers: {
        apikey: SUPABASE_KEY,
        Authorization: `Bearer ${session.access_token}`,
      },
    }).catch(() => undefined);
  }
  clearSession();
}

async function control<T>(payload: Record<string, unknown>): Promise<T> {
  const session = getSession();
  if (!session?.access_token) throw new Error('AUTH_REQUIRED');
  const res = await fetch(CONTROL_URL, {
    method: 'POST',
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${session.access_token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    cache: 'no-store',
  });
  if (res.status === 401 || res.status === 403) {
    if (res.status === 401) clearSession();
    throw new Error('AUTH_REQUIRED');
  }
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`CONTROL_${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const pauliControl = {
  overview: () => control<PauliOverview>({ action: 'overview', org_slug: 'paulis-place' }),
  createMission: (mission: {
    title: string;
    intent: string;
    requested_outcome: string;
    language?: 'en' | 'es-MX' | 'mixed';
    mission_type?: string;
    autonomous_budget_cents?: number;
    required_completion_level?: 'IMPLEMENTED' | 'VERIFIED' | 'DEPLOYED' | 'HEALTHY' | 'OUTCOME_ACHIEVED' | 'BUSINESS_OUTCOME_MEASURED';
  }) => control<{ mission: PauliMissionSummary }>({ action: 'create_mission', org_slug: 'paulis-place', mission }),
  decideApproval: (approvalId: string, decision: 'approve' | 'deny', rationale = '') =>
    control<{ approval: PauliApprovalSummary }>({
      action: 'decide_approval',
      org_slug: 'paulis-place',
      approval_id: approvalId,
      decision,
      rationale,
    }),
};
