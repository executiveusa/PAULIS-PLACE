'use client';

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Briefcase,
  Check,
  CircleDollarSign,
  Home,
  LogOut,
  Mic,
  MicOff,
  Radio,
  Send,
  Sparkles,
  UserCheck,
  X,
} from 'lucide-react';
import {
  captureMagicLinkSession,
  getSession,
  pauliControl,
  PauliApprovalSummary,
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

function money(cents: number | null | undefined) {
  if (cents === null || cents === undefined || !Number.isFinite(Number(cents))) return 'Unknown';
  return `$${(Number(cents) / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function humanize(value: string) {
  return value.replace(/[._-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function coverageText(status?: string) {
  if (status === 'complete') return 'Verified';
  if (status === 'stale') return 'Needs refresh';
  if (status === 'partial') return 'Partial data';
  return 'Not connected';
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
      else setError(err instanceof Error ? err.message : 'Pauli is temporarily unavailable');
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
      for (let i = event.resultIndex; i < event.results.length; i += 1) transcript += event.results[i][0].transcript;
      setIntent(transcript.trim());
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    return () => recognition.stop();
  }, [language]);

  const canSubmit = useMemo(
    () => intent.trim().length >= 3 && outcome.trim().length >= 3 && !submitting,
    [intent, outcome, submitting],
  );

  async function onAuth(event: FormEvent) {
    event.preventDefault();
    setAuthMessage('');
    try {
      await requestMagicLink(authEmail.trim());
      setAuthMessage("Secure sign-in link sent. Open it on this device to enter Pauli's Place.");
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
        mission_type: 'owner-intent',
        autonomous_budget_cents: 0,
        required_completion_level: 'OUTCOME_ACHIEVED',
      });
      setIntent('');
      setOutcome('');
      await loadOverview();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pauli could not start that mission');
    } finally {
      setSubmitting(false);
    }
  }

  function toggleListening() {
    const recognition = recognitionRef.current;
    if (!recognition) {
      setError('Voice input is not available in this browser. Type your request instead.');
      return;
    }
    if (listening) {
      recognition.stop();
      setListening(false);
      return;
    }
    recognition.lang = language === 'es-MX' ? 'es-MX' : 'en-US';
    recognition.start();
    setListening(true);
  }

  async function decide(approval: PauliApprovalSummary, decision: 'approve' | 'deny') {
    await pauliControl.decideApproval(
      approval.id,
      decision,
      decision === 'approve' ? 'Approved by owner from Pauli Home' : 'Declined by owner from Pauli Home',
    );
    await loadOverview();
  }

  if (authRequired) {
    return (
      <div className="min-h-screen bg-[#f3f0ea] text-[#171714] flex items-center justify-center p-6">
        <div className="w-full max-w-md rounded-[2rem] border border-black/10 bg-white p-8 shadow-[0_24px_80px_rgba(0,0,0,.08)]">
          <div className="text-[11px] font-semibold tracking-[0.26em] uppercase text-black/45">Pauli&apos;s Place</div>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">Your business, one conversation away.</h1>
          <p className="mt-4 text-sm leading-6 text-black/55">Sign in to talk to Pauli, see what is working, and approve only the decisions that need you.</p>
          <form onSubmit={onAuth} className="mt-8 space-y-3">
            <input type="email" required value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} placeholder="you@example.com" className="w-full rounded-2xl border border-black/10 bg-[#faf9f6] px-4 py-3.5 text-sm outline-none focus:border-black/30" />
            <button className="w-full rounded-2xl bg-[#171714] px-4 py-3.5 text-sm font-semibold text-white hover:bg-black">Send secure sign-in link</button>
          </form>
          {authMessage && <p className="mt-4 text-xs leading-5 text-black/50">{authMessage}</p>}
        </div>
      </div>
    );
  }

  const brief = overview?.owner_brief;
  const outcomeData = brief?.outcome;
  const topDecision = brief?.decisions?.[0];
  const coverage = outcomeData?.coverage_status ?? brief?.coverage_status ?? 'missing';
  const activeAgents = (overview?.agents ?? []).filter((agent) => ['working', 'meeting', 'recovering'].includes(agent.status));
  const blockedAgents = (overview?.agents ?? []).filter((agent) => ['blocked', 'error', 'waiting_approval'].includes(agent.status));

  return (
    <div className="min-h-screen bg-[#f3f0ea] text-[#171714] pb-24 md:pb-10">
      <header className="sticky top-0 z-30 border-b border-black/[0.06] bg-[#f3f0ea]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 md:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-full bg-[#171714] text-sm font-semibold text-white">P</div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/40">Pauli&apos;s Place</div>
              <div className="text-sm font-semibold tracking-[-0.02em]">Owner Home</div>
            </div>
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            <TopNav href="/" label="Home" active />
            <TopNav href="#pauli" label="Pauli" />
            <TopNav href="/missions" label="Work" />
            <TopNav href="/lounge" label="World" />
          </nav>
          <button onClick={async () => { await signOut(); setAuthRequired(true); setOverview(null); }} className="grid h-10 w-10 place-items-center rounded-full border border-black/10 bg-white/70 text-black/45 hover:text-black" aria-label="Sign out"><LogOut className="h-4 w-4" /></button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-6 md:px-8 md:py-10">
        <section className="grid gap-6 xl:grid-cols-[1.18fr_.82fr]">
          <div id="pauli" className="rounded-[2rem] bg-[#171714] p-6 text-white shadow-[0_28px_80px_rgba(0,0,0,.12)] md:p-9">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-full bg-white/10"><Sparkles className="h-5 w-5" /></div>
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-white/40">Pauli</div>
                <div className="text-sm text-white/70">Tell me the outcome. I&apos;ll handle the machinery underneath.</div>
              </div>
            </div>

            <h1 className="mt-8 max-w-3xl text-4xl font-semibold tracking-[-0.055em] md:text-6xl">What should we accomplish?</h1>
            <form onSubmit={onMission} className="mt-7 space-y-3">
              <div className="relative">
                <textarea value={intent} onChange={(event) => setIntent(event.target.value)} rows={4} placeholder="Find the best thing we can launch this week and get it ready for me to approve." className="w-full resize-none rounded-[1.5rem] border border-white/10 bg-white/[0.06] px-5 py-5 pr-16 text-base leading-7 text-white outline-none placeholder:text-white/30 focus:border-white/25" />
                <button type="button" onClick={toggleListening} aria-label="Talk to Pauli" className="absolute bottom-4 right-4 grid h-11 w-11 place-items-center rounded-full bg-white text-black transition hover:scale-[1.03]">{listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}</button>
              </div>
              <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                <input value={outcome} onChange={(event) => setOutcome(event.target.value)} placeholder="Success looks like… verified, ready for approval, with evidence" className="rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3.5 text-sm text-white outline-none placeholder:text-white/30 focus:border-white/25" />
                <div className="flex gap-2">
                  <select value={language} onChange={(event) => setLanguage(event.target.value as typeof language)} className="rounded-2xl border border-white/10 bg-[#242420] px-3 py-3 text-sm text-white outline-none"><option value="en">English</option><option value="es-MX">Español</option><option value="mixed">Mixed</option></select>
                  <button disabled={!canSubmit} className="flex min-w-32 items-center justify-center gap-2 rounded-2xl bg-white px-5 py-3.5 text-sm font-semibold text-black disabled:opacity-30">{submitting ? 'Starting…' : 'Go'} <Send className="h-4 w-4" /></button>
                </div>
              </div>
            </form>
            <p className="mt-4 text-xs leading-5 text-white/35">Pauli can do reversible work autonomously. Production launches, public sends, and consequential spend still come back to you for approval.</p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <MoneyCard label="Revenue" value={money(outcomeData?.revenue_cents)} sublabel={coverageText(coverage)} coverage={coverage} icon={CircleDollarSign} />
            <MoneyCard label="Profit" value={money(outcomeData?.profit_cents)} sublabel={outcomeData?.cost_cents == null ? 'Costs unknown until coverage is verified' : `${money(outcomeData.cost_cents)} covered cost`} coverage={coverage} icon={Briefcase} />
          </div>
        </section>

        {error && <div className="mt-5 flex items-start gap-3 rounded-2xl border border-red-900/10 bg-red-50 p-4 text-sm text-red-950"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><div><div className="font-semibold">Pauli hit a real blocker.</div><div className="mt-1 text-red-900/65">{error}. Nothing is being reported as complete while this is unresolved.</div></div></div>}

        <section className="mt-8 grid gap-6 lg:grid-cols-2">
          <section>
            <SectionHeader eyebrow="Needs You" title={overview?.approvals_pending ? `${overview.approvals_pending} decision${overview.approvals_pending === 1 ? '' : 's'} waiting` : 'Nothing needs your approval'} subtitle="Only consequential decisions interrupt you." />
            <div className="mt-4 space-y-3">
              {(overview?.approvals ?? []).slice(0, 4).map((approval) => (
                <div key={approval.id} className="rounded-[1.5rem] border border-black/[0.07] bg-white p-5 shadow-[0_12px_40px_rgba(0,0,0,.04)]">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-black/35">{humanize(approval.risk_class)} action</div>
                      <h3 className="mt-2 text-lg font-semibold tracking-[-0.025em]">{humanize(approval.action_class)}</h3>
                      <p className="mt-2 text-sm leading-6 text-black/50">{approval.max_spend_cents ? `Maximum authorized spend: ${money(approval.max_spend_cents)}.` : 'No spend is authorized by this approval.'} Scope stays limited to this action.</p>
                    </div>
                    <UserCheck className="h-5 w-5 shrink-0 text-black/35" />
                  </div>
                  <div className="mt-5 flex gap-2">
                    <button onClick={() => void decide(approval, 'deny')} className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-black/10 px-4 py-3 text-sm font-semibold"><X className="h-4 w-4" /> Decline</button>
                    <button onClick={() => void decide(approval, 'approve')} className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-[#171714] px-4 py-3 text-sm font-semibold text-white"><Check className="h-4 w-4" /> Approve</button>
                  </div>
                </div>
              ))}
              {!loading && !overview?.approvals?.length && <EmptyCard label="Pauli is handling the reversible work. You only appear here when your judgment is actually required." />}
            </div>
          </section>

          <section>
            <SectionHeader eyebrow="Working Now" title={activeAgents.length ? `${activeAgents.length} agent${activeAgents.length === 1 ? '' : 's'} moving work forward` : 'No agents are actively working'} subtitle="Real runtime state only. No decorative activity." />
            <div className="mt-4 rounded-[1.5rem] border border-black/[0.07] bg-white p-5 shadow-[0_12px_40px_rgba(0,0,0,.04)]">
              <div className="space-y-1">
                {activeAgents.slice(0, 5).map((agent) => (
                  <div key={agent.id} className="flex items-center justify-between gap-4 rounded-xl px-2 py-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#f3f0ea] text-xs font-semibold">{agent.name.slice(0, 1)}</div>
                      <div className="min-w-0"><div className="truncate text-sm font-semibold">{agent.name}</div><div className="truncate text-xs text-black/40">{humanize(agent.role)}</div></div>
                    </div>
                    <StateDot status={agent.status} />
                  </div>
                ))}
                {!activeAgents.length && <p className="px-2 py-4 text-sm leading-6 text-black/45">Pauli will show active work here when a mission is running.</p>}
              </div>
              {blockedAgents.length > 0 && <div className="mt-4 rounded-xl bg-[#fff2e7] p-3 text-xs leading-5 text-[#7a3c0a]">{blockedAgents.length} agent{blockedAgents.length === 1 ? '' : 's'} blocked or waiting for approval. Pauli will not hide the failure state.</div>}
              <Link href="/agents" className="mt-4 flex items-center justify-between border-t border-black/[0.06] pt-4 text-sm font-semibold">See workforce <ArrowRight className="h-4 w-4" /></Link>
            </div>
          </section>
        </section>

        <section className="mt-10 grid gap-6 xl:grid-cols-[1fr_.72fr]">
          <section>
            <SectionHeader eyebrow="What changed" title={topDecision ? topDecision.reason : 'No new business decision yet'} subtitle={brief?.as_of ? `Source-qualified through ${new Date(brief.as_of).toLocaleString()}` : 'Financial coverage has not been established yet.'} />
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <SmallOutcome label="POD live" value={outcomeData?.pod_published ?? 0} />
              <SmallOutcome label="Digital sell-ready" value={outcomeData?.digital_sell_ready ?? 0} />
              <SmallOutcome label="Software previews" value={outcomeData?.software_preview_ready ?? 0} />
            </div>
            {topDecision && <div className="mt-3 rounded-[1.5rem] bg-[#dbe7d8] p-5"><div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#31502d]/60">Pauli recommends</div><div className="mt-2 text-lg font-semibold tracking-[-0.025em] text-[#243d21]">{humanize(topDecision.action)}</div><p className="mt-2 text-sm leading-6 text-[#31502d]/70">{topDecision.reason}</p></div>}
          </section>

          <section>
            <SectionHeader eyebrow="Recent work" title={`${overview?.active_missions ?? 0} active mission${overview?.active_missions === 1 ? '' : 's'}`} subtitle="Outcomes first. Technical traces stay one level deeper." />
            <div className="mt-4 overflow-hidden rounded-[1.5rem] border border-black/[0.07] bg-white">
              {(overview?.missions ?? []).slice(0, 5).map((mission) => (
                <Link key={mission.id} href="/missions" className="flex items-center justify-between gap-4 border-b border-black/[0.06] p-4 last:border-0 hover:bg-black/[0.015]">
                  <div className="min-w-0"><div className="truncate text-sm font-semibold">{mission.title}</div><div className="mt-1 truncate text-xs text-black/40">{mission.requested_outcome}</div></div>
                  <span className="shrink-0 rounded-full bg-[#f3f0ea] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-black/45">{humanize(mission.status)}</span>
                </Link>
              ))}
              {!loading && !overview?.missions?.length && <EmptyCard label="No recent missions. Tell Pauli what outcome you want." compact />}
            </div>
          </section>
        </section>

        {!!overview?.incidents?.length && <section className="mt-8 rounded-[1.5rem] border border-red-950/10 bg-[#fff4f0] p-5"><div className="flex items-center gap-2 text-sm font-semibold text-red-950"><AlertTriangle className="h-4 w-4" /> Something needs repair</div><div className="mt-3 space-y-2">{overview.incidents.slice(0, 3).map((incident) => <div key={incident.id} className="text-sm leading-6 text-red-950/65"><span className="font-semibold text-red-950">{incident.title}.</span> {incident.summary}</div>)}</div></section>}
      </main>

      <nav className="fixed inset-x-3 bottom-3 z-40 grid grid-cols-4 rounded-[1.4rem] border border-black/10 bg-white/95 p-1.5 shadow-[0_18px_60px_rgba(0,0,0,.15)] backdrop-blur md:hidden">
        <BottomNav href="/" label="Home" icon={Home} active />
        <BottomNav href="#pauli" label="Pauli" icon={Sparkles} />
        <BottomNav href="/missions" label="Work" icon={Activity} />
        <BottomNav href="/lounge" label="World" icon={Radio} />
      </nav>
    </div>
  );
}

function TopNav({ href, label, active = false }: { href: string; label: string; active?: boolean }) {
  return <Link href={href} className={`rounded-full px-4 py-2 text-sm font-semibold transition ${active ? 'bg-white shadow-sm' : 'text-black/45 hover:text-black'}`}>{label}</Link>;
}

function BottomNav({ href, label, icon: Icon, active = false }: { href: string; label: string; icon: any; active?: boolean }) {
  return <Link href={href} className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[10px] font-semibold ${active ? 'bg-[#171714] text-white' : 'text-black/45'}`}><Icon className="h-4 w-4" />{label}</Link>;
}

function SectionHeader({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle: string }) {
  return <div><div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/35">{eyebrow}</div><h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">{title}</h2><p className="mt-2 max-w-xl text-sm leading-6 text-black/45">{subtitle}</p></div>;
}

function MoneyCard({ label, value, sublabel, coverage, icon: Icon }: { label: string; value: string; sublabel: string; coverage: string; icon: any }) {
  const warning = coverage !== 'complete';
  return <div className="rounded-[2rem] border border-black/[0.07] bg-white p-6 shadow-[0_14px_50px_rgba(0,0,0,.045)]"><div className="flex items-center justify-between"><div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/35">{label}</div><div className="grid h-10 w-10 place-items-center rounded-full bg-[#f3f0ea]"><Icon className="h-4 w-4" /></div></div><div className="mt-7 text-4xl font-semibold tracking-[-0.055em]">{value}</div><div className={`mt-3 text-xs ${warning ? 'text-amber-700' : 'text-black/40'}`}>{sublabel}</div></div>;
}

function SmallOutcome({ label, value }: { label: string; value: number }) {
  return <div className="rounded-[1.5rem] border border-black/[0.07] bg-white p-5"><div className="text-3xl font-semibold tracking-[-0.045em]">{value}</div><div className="mt-2 text-xs font-medium text-black/40">{label}</div></div>;
}

function StateDot({ status }: { status: string }) {
  const good = ['working', 'meeting'].includes(status);
  const warning = ['recovering', 'waiting_approval'].includes(status);
  return <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ${good ? 'bg-emerald-50 text-emerald-700' : warning ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}`}>{humanize(status)}</span>;
}

function EmptyCard({ label, compact = false }: { label: string; compact?: boolean }) {
  return <div className={`${compact ? 'p-4' : 'rounded-[1.5rem] border border-dashed border-black/10 bg-white/40 p-5'} text-sm leading-6 text-black/40`}>{label}</div>;
}
