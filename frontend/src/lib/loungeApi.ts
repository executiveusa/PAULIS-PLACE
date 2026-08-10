// Pauli's World API helpers. This layer is truth-only: when the backend is unavailable,
// callers receive an explicit error instead of synthetic activity.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
      ...init,
    });
  } catch (error) {
    throw new Error(`Pauli backend unavailable for ${path}: ${error instanceof Error ? error.message : 'network error'}`);
  }
  if (!res.ok) throw new Error(`Pauli API ${res.status} for ${path}: ${await res.text()}`);
  return res.json();
}

export interface HermesHealth {
  status: 'ok' | 'cap_reached' | 'offline';
  spent_usd: number;
  cap_usd: number;
  remaining_usd: number;
  routes_known: number;
  laws: { L1: string; L2: string; L3: string; L4: string };
}

export interface Envelope {
  event_id: string;
  route: string;
  stage: string;
  ts: string;
  services_touched: string[];
  blast_radius_usd: number;
  worker_profile: string;
  worker_model: string;
  judge_verdict: string | null;
  judge_model: string | null;
  envelope_version: string;
  next_action: string | null;
  body: any;
  halt?: boolean;
  halt_id?: string;
}

export interface LoungeAvatarState {
  id: string;
  name: string;
  position: [number, number, number];
  model: string;
  state: string;
}
export interface LoungeState {
  lounge: string;
  setting: string;
  avatars: LoungeAvatarState[];
  schedule_cue: string;
}

export const AVATAR_ROSTER = [
  { id: 'pauli', name: 'Pauli', role: 'Executive agent' },
  { id: 'scout', name: 'Scout', role: 'Research' },
  { id: 'strategist', name: 'Strategist', role: 'Strategy' },
  { id: 'builder', name: 'Builder', role: 'Engineering' },
  { id: 'critic', name: 'Critic', role: 'Gauntlet' },
  { id: 'guardian', name: 'Guardian', role: 'Safety & policy' },
  { id: 'publisher', name: 'Publisher', role: 'Deployment' },
  { id: 'sales', name: 'Sales', role: 'Revenue' },
] as const;

export const hemmes = {
  health: () => fetchAPI<HermesHealth>('/api/hermes/health'),
  envelopes: (limit?: number) => fetchAPI<{ envelopes: Envelope[] }>(`/api/envelopes/recent?limit=${limit ?? 30}`),
};
export const lounge = {
  state: () => fetchAPI<LoungeState>('/api/lounge/state'),
  scenes: (limit?: number) => fetchAPI<{ scenes: Envelope[] }>(`/api/lounge/scenes?limit=${limit ?? 20}`),
};
export const voice = {
  command: (transcript: string) => fetchAPI<Envelope>('/api/voice/command', {
    method: 'POST',
    body: JSON.stringify({ transcript }),
  }),
};
