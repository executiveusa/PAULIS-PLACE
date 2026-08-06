// Yappyverse API helpers for the lounge + observation
// Backend: http://localhost:8000 or NEXT_PUBLIC_API_BASE_URL

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function fetchAPI<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export interface HermesHealth {
  status: 'ok' | 'cap_reached';
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

export const hemmes = {
  health: () => fetchAPI<HermesHealth>('/api/hermes/health'),
  envelopes: (limit?: number) =>
    fetchAPI<{ envelopes: Envelope[] }>(`/api/envelopes/recent?limit=${limit ?? 30}`),
};

export const lounge = {
  state: () => fetchAPI<LoungeState>('/api/lounge/state'),
  scenes: (limit?: number) => fetchAPI<{ scenes: Envelope[] }>(`/api/lounge/scenes?limit=${limit ?? 20}`),
};

export const voice = {
  command: (transcript: string) =>
    fetchAPI<Envelope>('/api/voice/command', {
      method: 'POST',
      body: JSON.stringify({ transcript }),
    }),
};