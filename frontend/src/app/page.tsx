'use client';

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  CircleDollarSign,
  LogOut,
  Mic,
  MicOff,
  Radio,
  Send,
  ShieldCheck,
  Users,
  Volume2,
} from 'lucide-react';
import {
  captureMagicLinkSession,
  getSession,
  pauliControl,
  PauliOverview,
  requestMagicLink,
  signOut,
} from '@/lib/pauliControl';

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: any) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
};

function money(cents: number | string) {
  const value = typeof cents === 'string' ? Number(cents) : cents;
  return `$${(Number.isFinite(value) ? value : 0 / 100).toFixed ? (Number(value || 0) / 100).toFixed(2) : '0.00'}`;
}

export default function PauliHome() {
  const [overview, setOverview] = useState<PauliOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [authRequired, setAuthRequired] = useState(false);
  const [authEmail, setAuthEmail] = useState('');
  const [authMessage, setAuthMessage] = useState('');
  const [intent, setIntent] = useState('');
  const [outcome, setOutcome] = useState('');
  const [language, setLanguage] = useState<'en' | 'es-MX' | 'mixed'>('en');
  const [budget, setBudget] = useState(10);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const loadOverview = useCallback(async () => {
    try {
      setError('');
      const data = await pauliControl.overview();
      setOverview(data);
      setAuthRequired(false);
    } catch (err) {
      if (String(err).includes('AUTH_REQUIRED')) setAuthRequired(true);
      else setError(err instanceof Error ? err.message : 'Control plane unavailable');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    captureMagicLinkSession();
    setAuthRequired(!getSession());
    void loadOverview();
    const interval = window.setInterval(loadOverview, 15000);
    return () => window.clearInterval(interval);
  }, [loadOverview]);

  useEffect(() => {
    const W = window as any;
    const Recognition = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (!Recognition) return;
    const recognition: SpeechRecognitionLike = new Recognition();
    recognition.lang = language === 'es-MX' ? 'es-MX' : 'en-US';
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.onresult = (event: any) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript;
      }
      setIntent(transcript.trim());
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    return () => recognition.stop();
  }, [language]);

  const canSubmit = useMemo(() => intent.trim().length >= 3 && outcome.trim().length >= 3 && !submitting, [intent, outcome, submitting]);

  async function onAuth(event: FormEvent) {
    event.preventDefault();
    setAuthMessage('');
    try {
      await requestMagicLink(authEmail.trim());
      setAuthMessage('Secure sign-in link sent. Open it on this device to enter Pauli\'s Place.');
    } catch (err) {
      setAuthMessage(err instanceof Error ? err.message : 'Unable to send sign-in link');
    }
  }

  async function onMission(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError('');
    try {
      const title = intent.trim().split(/[.!?]/)[0].slice(0, 72) || 'Pauli mission';
      await pauliControl.createMission({
        title,
        intent: intent.trim(),
        requested_outcome: outcome.trim(),
        language,
        mission_type: 'voice-intent',
        autonomous_budget_cents: Math.max(0, Math.min(25, budget)) * 100,
        required_completion_level: 'OUTCOME_ACHIEVED',
      });
      setIntent('');
      setOutcome('');
      await loadOverview();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Mission creation failed');
    } finally {
      setSubmitting(false);
    }
  }

  function toggleListening() {
    const recognition = recognitionRef.current;
    if (!recognition) {
      setError('Voice recognition is not available in this browser. Type the mission instead.');
      return;
    }
    if (listening) {
      recognition.stop();
      setListening(false);
    } else {
      recognition.lang = language === 'es-MX' ? 'es-MX' : 'en-US';
      recognition.start();
      setListening(true);
    }
  }

  if (authRequired) {
    return (
      <div className="min-h-screen bg-[#080808] text-stone-100 flex items-center justify-center p-6">
        <div className="w-full max-w-md border border-white/10 bg-[#111]/95 p-8 shadow-2xl">
          <div className="text-[11px] tracking-[0.35em] uppercase text-amber-200/70">Pauli's Place</div>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight">Owner access</h1>
          <p className="mt-3 text-sm leading-6 text-stone-400">Mission Control is private. Sign in with the email authorized for this workspace.</p>
          <form onSubmit={onAuth} className="mt-7 space-y-4">
            <input
              type="email"
              required
              value={authEmail}
              onChange={(event) => setAuthEmail(event.target.value)}
              placeholder="you@example.com"
              className="w-full border border-white/10 bg-black/40 px-4 py-3 text-sm outline-none focus:border-amber-200/50"
            />
            <button className="w-full bg-stone-100 px-4 py-3 text-sm font-semibold text-black hover:bg-white">Send secure sign-in link</button>
          </form>
          {authMessage && <p className="mt-4 text-xs leading-5 text-stone-400">{authMessage}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-[#080808] text-stone-100">
      <header className="border-b border-white/10 px-6 py-5 lg:px-10">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6">
          <div>
            <div className="text-[10px] tracking-[0.38em] uppercase text-amber-200/60">Autonomous business operating environment</div>
            <h1 className="mt-2 text-2xl font-semibold">What are we getting done?</h1>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/lounge" className="hidden sm:flex items-center gap-2 border border-white/10 px-4 py-2 text-sm hover:border-amber-200/40">
              <Radio className="h-4 w-4" /> Enter Pauli's World
            </Link>
            <button
              onClick={async () => { await signOut(); setAuthRequired(true); setOverview(null); }}
              className="border border-white/10 p-2 text-stone-400 hover:text-white"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-8 px-6 py-8 lg:px-10">
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
          <Metric label="Active missions" value={overview?.active_missions ?? 0} icon={Activity} />
          <Metric label="Agents working" value={overview?.agents_working ?? 0} icon={Users} />
          <Metric label="Approvals" value={overview?.approvals_pending ?? 0} icon={ShieldCheck} />
          <Metric label="Incidents" value={overview?.open_incidents ?? 0} icon={AlertTriangle} />
          <Metric label="Revenue today" value={money(overview?.revenue_today_cents ?? 0)} icon={CircleDollarSign} />
          <Metric label="Spend today" value={money(overview?.spend_today_cents ?? 0)} icon={CircleDollarSign} />
        </section>

        <section className="grid gap-8 xl:grid-cols-[1.3fr_.7fr]">
          <div className="border border-white/10 bg-[#0e0e0e] p-6 lg:p-8">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full border border-amber-200/30 bg-amber-200/5">
                <Volume2 className="h-4 w-4 text-amber-100" />
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.25em] text-stone-500">Talk to Pauli</div>
                <div className="text-sm text-stone-300">Intent becomes a durable mission. No fake success state.</div>
              </div>
            </div>

            <form onSubmit={onMission} className="mt-7 space-y-5">
              <div className="relative">
                <textarea
                  value={intent}
                  onChange={(event) => setIntent(event.target.value)}
                  placeholder="Pauli, find a nonprofit with a weak website, research it, and build a superior prototype."
                  rows={5}
                  className="w-full resize-none border border-white/10 bg-black/40 px-4 py-4 pr-14 text-base leading-7 outline-none placeholder:text-stone-600 focus:border-amber-200/40"
                />
                <button type="button" onClick={toggleListening} className="absolute bottom-4 right-4 rounded-full border border-white/10 p-3 hover:border-amber-200/40" aria-label="Toggle microphone">
                  {listening ? <MicOff className="h-5 w-5 text-amber-100" /> : <Mic className="h-5 w-5 text-stone-400" />}
                </button>
              </div>

              <input
                value={outcome}
                onChange={(event) => setOutcome(event.target.value)}
                placeholder="Requested outcome — e.g. verified live preview with evidence"
                className="w-full border border-white/10 bg-black/40 px-4 py-3 text-sm outline-none focus:border-amber-200/40"
              />

              <div className="grid gap-3 sm:grid-cols-3">
                <select value={language} onChange={(event) => setLanguage(event.target.value as typeof language)} className="border border-white/10 bg-black/40 px-3 py-3 text-sm outline-none">
                  <option value="en">English</option>
                  <option value="es-MX">Español (México)</option>
                  <option value="mixed">Mixed / bilingual</option>
                </select>
                <label className="flex items-center justify-between gap-3 border border-white/10 bg-black/40 px-3 py-3 text-sm text-stone-400 sm:col-span-1">
                  Autonomous budget
                  <span className="text-stone-100">${budget}</span>
                </label>
                <input type="range" min={0} max={25} value={budget} onChange={(event) => setBudget(Number(event.target.value))} className="w-full accent-stone-100" />
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs leading-5 text-stone-500">External sends, production promotion, irreversible actions, and spend beyond scope still require approval.</p>
                <button disabled={!canSubmit} className="flex shrink-0 items-center justify-center gap-2 bg-stone-100 px-5 py-3 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-30">
                  {submitting ? 'Creating mission…' : 'Create mission'} <Send className="h-4 w-4" />
                </button>
              </div>
            </form>
          </div>

          <div className="space-y-4">
            <PanelTitle title="System truth" subtitle="Provider and incident state from the control plane" />
            <div className="space-y-2">
              {(overview?.providers ?? []).slice(0, 6).map((provider) => (
                <div key={provider.provider_key} className="flex items-center justify-between border border-white/10 bg-[#0e0e0e] px-4 py-3">
                  <div>
                    <div className="text-sm font-medium">{provider.name}</div>
                    <div className="text-xs text-stone-500">{provider.kind}</div>
                  </div>
                  <StatusPill status={provider.health_status} />
                </div>
              ))}
              {!loading && !overview?.providers?.length && <Empty label="No runtime providers registered." />}
            </div>
            {(overview?.incidents ?? []).map((incident) => (
              <div key={incident.id} className="border border-red-400/20 bg-red-950/10 p-4">
                <div className="text-xs uppercase tracking-wider text-red-300">{incident.severity}</div>
                <div className="mt-1 text-sm font-medium">{incident.title}</div>
                <p className="mt-1 text-xs leading-5 text-stone-500">{incident.summary}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-8 lg:grid-cols-2">
          <div>
            <PanelTitle title="Mission board" subtitle="Newest durable objectives" />
            <div className="mt-3 divide-y divide-white/10 border border-white/10 bg-[#0e0e0e]">
              {(overview?.missions ?? []).map((mission) => (
                <div key={mission.id} className="flex items-center justify-between gap-5 p-4">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{mission.title}</div>
                    <div className="mt-1 line-clamp-1 text-xs text-stone-500">{mission.requested_outcome}</div>
                  </div>
                  <StatusPill status={mission.status} />
                </div>
              ))}
              {!loading && !overview?.missions?.length && <Empty label="No missions yet. Tell Pauli what outcome you want." />}
            </div>
          </div>

          <div>
            <PanelTitle title="Agents" subtitle="Persistent identities; model providers are replaceable" />
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {(overview?.agents ?? []).slice(0, 10).map((agent) => (
                <div key={agent.id} className="border border-white/10 bg-[#0e0e0e] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium">{agent.name}</div>
                      <div className="text-xs text-stone-500">{agent.role}</div>
                    </div>
                    <StatusPill status={agent.status} />
                  </div>
                  {agent.world_location_key && <div className="mt-3 text-[10px] uppercase tracking-[0.2em] text-stone-600">{agent.world_location_key}</div>}
                </div>
              ))}
            </div>
          </div>
        </section>

        {!!overview?.approvals?.length && (
          <section>
            <PanelTitle title="Decisions required" subtitle="Scoped authority only — approve the action, not the entire agent" />
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              {overview.approvals.map((approval) => (
                <div key={approval.id} className="border border-amber-200/20 bg-amber-100/[0.03] p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-xs uppercase tracking-[0.22em] text-amber-100/60">{approval.risk_class}</div>
                      <div className="mt-2 text-base font-medium">{approval.action_class}</div>
                      <div className="mt-1 text-xs text-stone-500">{approval.max_spend_cents ? `Maximum spend ${money(approval.max_spend_cents)}` : 'No spend scope'}</div>
                    </div>
                    <button
                      onClick={async () => { await pauliControl.decideApproval(approval.id, 'approve', 'Approved from Mission Control'); await loadOverview(); }}
                      className="flex items-center gap-2 bg-stone-100 px-3 py-2 text-xs font-semibold text-black"
                    >
                      Approve <CheckCircle2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {error && <div className="border border-red-400/20 bg-red-950/10 p-4 text-sm text-red-200">{error}</div>}

        <Link href="/lounge" className="group flex items-center justify-between border-y border-white/10 py-7">
          <div>
            <div className="text-xs uppercase tracking-[0.3em] text-stone-500">Observable world</div>
            <div className="mt-2 text-xl font-medium">Watch the work move through Pauli's World</div>
          </div>
          <ArrowRight className="h-5 w-5 text-stone-500 transition-transform group-hover:translate-x-1" />
        </Link>
      </main>
    </div>
  );
}

function Metric({ label, value, icon: Icon }: { label: string; value: string | number; icon: any }) {
  return (
    <div className="border border-white/10 bg-[#0e0e0e] p-4">
      <Icon className="h-4 w-4 text-amber-100/60" />
      <div className="mt-5 text-2xl font-semibold tabular-nums">{value}</div>
      <div className="mt-1 text-[10px] uppercase tracking-[0.2em] text-stone-500">{label}</div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const normalized = String(status || 'unknown').toLowerCase();
  const active = ['ready', 'healthy', 'working', 'active', 'executing', 'verified', 'deployed', 'outcome_achieved'].some((key) => normalized.includes(key));
  const bad = ['failed', 'error', 'blocked', 'critical', 'offline'].some((key) => normalized.includes(key));
  const classes = bad ? 'border-red-400/20 text-red-300' : active ? 'border-emerald-400/20 text-emerald-300' : 'border-white/10 text-stone-400';
  return <span className={`border px-2 py-1 text-[10px] uppercase tracking-wider ${classes}`}>{status || 'unknown'}</span>;
}

function PanelTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h2 className="text-base font-medium">{title}</h2>
      <p className="mt-1 text-xs text-stone-500">{subtitle}</p>
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return <div className="p-5 text-sm text-stone-600">{label}</div>;
}
