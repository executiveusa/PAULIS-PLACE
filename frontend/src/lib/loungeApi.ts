// Yappyverse API helpers for the lounge + observation
// Backend: http://localhost:8000 or NEXT_PUBLIC_API_BASE_URL
import { demo, AVATAR_ROSTER } from './demo';

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

function withDemo<T>(real: () => Promise<T>, demoFn: () => T | Promise<T>): Promise<T> {
  return real().catch(() => (demoFn() as Promise<T>));
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
  health: () => withDemo(() => fetchAPI<HermesHealth>('/api/hermes/health'), () => demo.health()),
  envelopes: (limit?: number) =>
    withDemo<{ envelopes: Envelope[] }>(() => fetchAPI<{ envelopes: Envelope[] }>(`/api/envelopes/recent?limit=${limit ?? 30}`), () => demo.envelopes(limit ?? 30)),
};

export const lounge = {
  state: () => withDemo<LoungeState>(() => fetchAPI<LoungeState>('/api/lounge/state'), () => demo.loungeState()),
  scenes: (limit?: number) =>
    withDemo<{ scenes: Envelope[] }>(() => fetchAPI<{ scenes: Envelope[] }>(`/api/lounge/scenes?limit=${limit ?? 20}`), () => demo.scenes(limit ?? 20)),
};

export const voice = {
  command: (transcript: string) =>
    withDemo<Envelope>(
      () =>
        fetchAPI<Envelope>('/api/voice/command', {
          method: 'POST',
          body: JSON.stringify({ transcript }),
        }),
      () => demo.envelopes(1).then((r) => r.envelopes[0])
    ),
};

export { AVATAR_ROSTER };