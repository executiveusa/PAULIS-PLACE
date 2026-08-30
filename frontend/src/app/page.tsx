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
  PauliAgentSummary,
  PauliApprovalSummary,
  PauliOverview,
  requestMagicLink,
  signOut,
} from '@/lib/pauliControl';
import {
  AgentDetailSheet,
  FeedbackStack,
  PremiumFeedback,
} from '@/components/PremiumInteractions';

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
  const [decisionBusy, setDecisionBusy] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [listening, setListening] = useState(false);
  const [feedback, setFeedback] = useState<PremiumFeedback[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<PauliAgentSummary | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const dismissFeedback = useCallback((id: string) => {
    setFeedback((items) => items.filter((item) => item.id !== id));
  }, []);

  const pushFeedback = useCallback((title: string, detail: string, tone: PremiumFeedback['tone'] = 'neutral') => {
    const id = typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    setFeedback((items) => [...items.filter((item) => item.id !== id), { id, title, detail, tone }].slice(-4));
    return id;
  }, []);

  const replaceFeedback = useCallback((id: string, title: string, detail: string, tone: PremiumFeedback['tone']) => {
    setFeedback((items) => items.map((item) => item.id === id ? { id, title, detail, tone } : item));
  }, []);

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
    const notice = pushFeedback('Sending secure link…', 'Pauli is requesting a private sign-in link.', 'neutral');
    try {
      await requestMagicLink(authEmail.trim());
      const message = "Secure sign-in link sent. Open it on this device to enter Pauli's Place.";
      setAuthMessage(message);
      replaceFeedback(notice, 'Sign-in link sent', 'Check your inbox and open the link on this device.', 'success');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to send sign-in link';
      setAuthMessage(message);
      replaceFeedback(notice, 'Sign-in failed', message, 'error');
    }
  }

  async function onMission(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError('');
    const notice = pushFeedback('Starting mission…', 'Turning your intent into durable work.', 'neutral');
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
      replaceFeedback(notice, 'Mission started', 'Pauli accepted the work. Progress will appear under Working Now.', 'success');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Pauli could not start that mission';
      setError(message);
      replaceFeedback(notice, 'Mission did not start', 'No success is being reported. Review the blocker below.', 'error');
    } finally {
      setSubmitting(false);
    }
  }

  function toggleListening() {
    const recognition = recognitionRef.current;
    if (!recognition) {
      const message = 'Voice input is not available in this browser. Type your request instead.';
      setError(message);
      pushFeedback('Voice is unavailable here', 'Type the request instead; nothing else is blocked.', 'warning');
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
    if (decisionBusy) return;
    setDecisionBusy(approval.id);
    const verb = decision === 'approve' ? 'Approving' : 'Declining';
    const notice = pushFeedback(`${verb} decision…`, humanize(approval.action_class), 'neutral');
    try {
      await pauliControl.decideApproval(
        approval.id,
        decision,
        decision === 'approve' ? 'Approved by owner from Pauli Home' : 'Declined by owner from Pauli Home',
      );
      await loadOverview();
      replaceFeedback(
        notice,
        decision === 'approve' ? 'Approved' : 'Declined',
        `${humanize(approval.action_class)} was ${decision === 'approve' ? 'approved' : 'declined'} within its recorded scope.`,
        decision === 'approve' ? 'success' : 'warning',
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : 'The decision could not be recorded';
      setError(message);
      replaceFeedback(notice, 'Decision was not recorded', message, 'error');
    } finally {
      setDecisionBusy(null);
    }
  }

  if (authRequired) {
    return (
      <div className="owner-shell min-h-screen text-[#171714] flex items-center justify-center p-6">
        <FeedbackStack items={feedback} onDismiss={dismissFeedback} />
        <div className="owner-card w-full max-w-md rounded-[2.2rem] p-8 md:p-10">
          <div className="flex items-center gap-3">
            <div className="brand-mark h-11 w-11 rounded-full text-sm font-semibold text-white">P</div>
            <div><div className="text-[10px] font-semibold tracking-[0.26em] uppercase text-black/40">Pauli&apos;s Place</div><div className="text-sm font-semibold">Private owner access</div></div>
          </div>
          <h1 className="mt-8 text-4xl font-semibold tracking-[-0.055em] md:text-5xl">Your business,<br />one conversation away.</h1>
          <p className="mt-5 text-sm leading-6 text-black/52">Sign in to talk to Pauli, see what is working, and approve only the decisions that actually need you.</p>
          <form onSubmit={onAuth} className="mt-8 space-y-3">
            <input type="email" required value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} placeholder="you@example.com" className="w-full rounded-2xl border border-black/10 bg-white/70 px-4 py-3.5 text-sm outline-none transition focus:border-black/30 focus:bg-white" />
            <button className="pressable w-full rounded-2xl bg-[#171714] px-4 py-3.5 text-sm font-semibold text-white hover:bg-black">Send secure sign-in link</button>
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
    <div className="owner-shell min-h-screen text-[#171714] pb-24 md:pb-10">
      <FeedbackStack items={feedback} onDismiss={dismissFeedback} />
      <AgentDetailSheet agent={selectedAgent} onClose={() => setSelectedAgent(null)} />

      <header className="owner-topbar sticky top-0 z-30">
        <div className="mx-auto flex max-w-[86rem] items-center justify-between px-5 py-4 md:px-8 lg:px-10">
          <Link href="/" className="pressable flex items-center gap-3 rounded-full">
            <div className="brand-mark h-10 w-10 rounded-full text-sm font-semibold text-white">P</div>
            <div><div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-black/38">Pauli&apos;s Place</div><div className="text-sm font-semibold tracking-[-0.02em]">Owner Home</div></div>
          </Link>
          <nav className="hidden items-center gap-1 rounded-full border border-black/[0.055] bg-white/50 p-1 md:flex">
            <TopNav href="/" label="Home" active />
            <TopNav href="#pauli" label="Pauli" />
            <TopNav href="/missions" label="Work" />
            <TopNav href="/lounge" label="World" />
          </nav>
          <button onClick={async () => { await signOut(); setAuthRequired(true); setOverview(null); }} className="pressable grid h-10 w-10 place-items-center rounded-full border border-black/10 bg-white/65 text-black/45 hover:bg-white hover:text-black" aria-label="Sign out"><LogOut className="h-4 w-4" /></button>
        </div>
      </header>

      <main className="mx-auto max-w-[86rem] px-5 py-7 md:px-8 md:py-10 lg:px-10">
        <section className="grid gap-5 xl:grid-cols-[1.35fr_.65fr]">
          <div id="pauli" className="pauli-stage rounded-[2.25rem] p-6 text-white md:p-9 lg:p-11">
            <div className="relative z-10 flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
              <div className="flex items-center gap-4">
                <PauliOrb active={activeAgents.length > 0 || submitting} />
                <div>
                  <div className="flex items-center gap-2"><div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-white/42">Pauli</div><span className="h-1 w-1 rounded-full bg-white/25" /><div className="text-[10px] uppercase tracking-[0.16em] text-white/35">Executive layer</div></div>
                  <div className="mt-1.5 max-w-md text-sm leading-6 text-white/66">Tell me the outcome. I&apos;ll handle the machinery underneath and bring you back only what needs judgment.</div>
                </div>
              </div>
              <div className="hidden rounded-full border border-white/10 bg-white/[0.055] px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/44 md:block">{activeAgents.length ? `${activeAgents.length} working now` : 'Ready for intent'}</div>
            </div>

            <div className="relative z-10 mt-10 max-w-4xl">
              <div className="mb-4 h-px w-20 bg-gradient-to-r from-[#d7c39b] to-transparent" />
              <h1 className="text-[2.7rem] font-semibold leading-[.96] tracking-[-0.065em] sm:text-5xl md:text-6xl lg:text-[4.9rem]">What should we<br className="hidden sm:block" /> accomplish?</h1>
              <p className="mt-5 max-w-2xl text-sm leading-6 text-white/46 md:text-base">One request becomes a durable mission, verified work, and a result you can trust.</p>
            </div>

            <form onSubmit={onMission} className="relative z-10 mt-8 space-y-3">
              <div className="relative">
                <textarea value={intent} onChange={(event) => setIntent(event.target.value)} rows={4} placeholder="Find the best thing we can launch this week and get it ready for me to approve." className="owner-input w-full resize-none rounded-[1.65rem] border border-white/10 bg-white/[0.055] px-5 py-5 pr-20 text-base leading-7 text-white outline-none placeholder:text-white/26 md:px-6 md:py-6" />
                <button type="button" onClick={toggleListening} aria-label="Talk to Pauli" className={`pressable absolute bottom-4 right-4 grid h-12 w-12 place-items-center rounded-full bg-[#f4efe4] text-black shadow-lg ${listening ? 'ring-4 ring-[#d7c39b]/20' : ''}`}>{listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}</button>
              </div>
              <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                <input value={outcome} onChange={(event) => setOutcome(event.target.value)} placeholder="Success looks like… verified, ready for approval, with evidence" className="owner-input rounded-2xl border border-white/10 bg-white/[0.055] px-4 py-3.5 text-sm text-white outline-none placeholder:text-white/26" />
                <div className="flex gap-2">
                  <select value={language} onChange={(event) => setLanguage(event.target.value as typeof language)} aria-label="Mission language" className="rounded-2xl border border-white/10 bg-[#292923] px-3 py-3 text-sm text-white outline-none"><option value="en">English</option><option value="es-MX">Español</option><option value="mixed">Mixed</option></select>
                  <button disabled={!canSubmit} className="pressable flex min-w-32 items-center justify-center gap-2 rounded-2xl bg-[#f4efe4] px-5 py-3.5 text-sm font-semibold text-black shadow-lg disabled:transform-none disabled:opacity-30">{submitting ? 'Starting…' : 'Go'} <Send className="h-4 w-4" /></button>
                </div>
              </div>
            </form>
            <div className="relative z-10 mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-white/32"><span>Reversible work runs autonomously.</span><span className="hidden h-1 w-1 rounded-full bg-white/20 sm:block" /><span>Production, public sends, and consequential spend come back to you.</span></div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <MoneyCard label="Revenue" value={money(outcomeData?.revenue_cents)} sublabel={coverageText(coverage)} coverage={coverage} icon={CircleDollarSign} />
            <MoneyCard label="Profit" value={money(outcomeData?.profit_cents)} sublabel={outcomeData?.cost_cents == null ? 'Costs unknown until coverage is verified' : `${money(outcomeData.cost_cents)} covered cost`} coverage={coverage} icon={Briefcase} profit />
          </div>
        </section>

        {error && <div className="mt-5 flex items-start gap-3 rounded-[1.4rem] border border-red-900/10 bg-red-50/90 p-4 text-sm text-red-950 shadow-sm"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><div><div className="font-semibold">Pauli hit a real blocker.</div><div className="mt-1 text-red-900/65">{error}. Nothing is being reported as complete while this is unresolved.</div></div></div>}

        <section className="mt-10 grid gap-7 lg:grid-cols-2">
          <section>
            <SectionHeader eyebrow="Needs You" title={overview?.approvals_pending ? `${overview.approvals_pending} decision${overview.approvals_pending === 1 ? '' : 's'} waiting` : 'Nothing needs your approval'} subtitle="Only consequential decisions interrupt you." />
            <div className="mt-4 space-y-3">
              {(overview?.approvals ?? []).slice(0, 4).map((approval) => (
                <div key={approval.id} className="owner-card approval-card rounded-[1.65rem] p-5 md:p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div><div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-black/35">{humanize(approval.risk_class)} action</div><h3 className="mt-2 text-xl font-semibold tracking-[-0.035em]">{humanize(approval.action_class)}</h3><p className="mt-2 max-w-xl text-sm leading-6 text-black/50">{approval.max_spend_cents ? `Maximum authorized spend: ${money(approval.max_spend_cents)}.` : 'No spend is authorized by this approval.'} Scope stays limited to this action.</p></div>
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#efe8d8]"><UserCheck className="h-4 w-4 text-black/55" /></div>
                  </div>
                  <div className="mt-5 flex gap-2">
                    <button disabled={decisionBusy === approval.id} onClick={() => void decide(approval, 'deny')} className="pressable flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl border border-black/10 bg-white/45 px-4 py-3 text-sm font-semibold disabled:opacity-45"><X className="h-4 w-4" /> Decline</button>
                    <button disabled={decisionBusy === approval.id} onClick={() => void decide(approval, 'approve')} className="pressable flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-[#171714] px-4 py-3 text-sm font-semibold text-white disabled:opacity-45"><Check className="h-4 w-4" /> Approve</button>
                  </div>
                </div>
              ))}
              {!loading && !overview?.approvals?.length && <EmptyCard label="Pauli is handling the reversible work. You only appear here when your judgment is actually required." />}
            </div>
          </section>

          <section>
            <SectionHeader eyebrow="Working Now" title={activeAgents.length ? `${activeAgents.length} agent${activeAgents.length === 1 ? '' : 's'} moving work forward` : 'No agents are actively working'} subtitle="Real runtime state only. Tap an agent for recorded detail." />
            <div className="owner-card mt-4 rounded-[1.65rem] p-5 md:p-6">
              <div className="space-y-1">
                {activeAgents.slice(0, 5).map((agent, index) => (
                  <button key={agent.id} type="button" onClick={() => setSelectedAgent(agent)} className="agent-row pressable flex w-full items-center justify-between gap-4 rounded-xl px-1 py-3 text-left" aria-label={`Open ${agent.name} details`}>
                    <div className="flex min-w-0 items-center gap-3">
                      <div className={`agent-avatar grid h-10 w-10 shrink-0 place-items-center rounded-full text-xs font-bold ${index % 3 === 0 ? 'bg-[#d9e3d3]' : index % 3 === 1 ? 'bg-[#e7d9bd]' : 'bg-[#d5e2e8]'}`}>{agent.name.slice(0, 1)}</div>
                      <div className="min-w-0"><div className="truncate text-sm font-semibold">{agent.name}</div><div className="truncate text-xs text-black/40">{humanize(agent.role)}</div></div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2"><StateDot status={agent.status} /><ArrowRight className="h-3.5 w-3.5 text-black/22" /></div>
                  </button>
                ))}
                {!activeAgents.length && <p className="px-1 py-5 text-sm leading-6 text-black/45">Pauli will show active work here when a mission is running.</p>}
              </div>
              {blockedAgents.length > 0 && <div className="mt-4 rounded-xl border border-[#e7b77e]/20 bg-[#fff2e7] p-3 text-xs leading-5 text-[#7a3c0a]">{blockedAgents.length} agent{blockedAgents.length === 1 ? '' : 's'} blocked or waiting for approval. Pauli will not hide the failure state.</div>}
              <Link href="/agents" className="pressable mt-4 flex min-h-12 items-center justify-between border-t border-black/[0.06] pt-4 text-sm font-semibold">See workforce <ArrowRight className="h-4 w-4" /></Link>
            </div>
          </section>
        </section>

        <div className="owner-rule my-10 h-px w-full" />

        <section className="grid gap-7 xl:grid-cols-[1fr_.72fr]">
          <section>
            <SectionHeader eyebrow="What changed" title={topDecision ? topDecision.reason : 'No new business decision yet'} subtitle={brief?.as_of ? `Source-qualified through ${new Date(brief.as_of).toLocaleString()}` : 'Financial coverage has not been established yet.'} />
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <SmallOutcome label="POD live" value={outcomeData?.pod_published ?? 0} tone="gold" />
              <SmallOutcome label="Digital sell-ready" value={outcomeData?.digital_sell_ready ?? 0} tone="sage" />
              <SmallOutcome label="Software previews" value={outcomeData?.software_preview_ready ?? 0} tone="blue" />
            </div>
            {topDecision && <div className="mt-3 rounded-[1.65rem] border border-[#31502d]/10 bg-[#dbe7d8]/85 p-5 shadow-sm md:p-6"><div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#31502d]/60">Pauli recommends</div><div className="mt-2 text-xl font-semibold tracking-[-0.035em] text-[#243d21]">{humanize(topDecision.action)}</div><p className="mt-2 text-sm leading-6 text-[#31502d]/70">{topDecision.reason}</p></div>}
          </section>

          <section>
            <SectionHeader eyebrow="Recent work" title={`${overview?.active_missions ?? 0} active mission${overview?.active_missions === 1 ? '' : 's'}`} subtitle="Outcomes first. Technical traces stay one level deeper." />
            <div className="owner-card mt-4 overflow-hidden rounded-[1.65rem]">
              {(overview?.missions ?? []).slice(0, 5).map((mission) => (
                <Link key={mission.id} href="/missions" className="pressable group flex min-h-16 items-center justify-between gap-4 border-b border-black/[0.055] p-4 last:border-0 hover:bg-white/55">
                  <div className="min-w-0"><div className="truncate text-sm font-semibold">{mission.title}</div><div className="mt-1 truncate text-xs text-black/40">{mission.requested_outcome}</div></div>
                  <div className="flex items-center gap-2"><span className="shrink-0 rounded-full bg-[#f3f0ea] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-black/45">{humanize(mission.status)}</span><ArrowRight className="h-4 w-4 text-black/25 transition group-hover:translate-x-0.5 group-hover:text-black/55" /></div>
                </Link>
              ))}
              {!loading && !overview?.missions?.length && <EmptyCard label="No recent missions. Tell Pauli what outcome you want." compact />}
            </div>
          </section>
        </section>

        {!!overview?.incidents?.length && <section className="mt-8 rounded-[1.5rem] border border-red-950/10 bg-[#fff4f0]/90 p-5"><div className="flex items-center gap-2 text-sm font-semibold text-red-950"><AlertTriangle className="h-4 w-4" /> Something needs repair</div><div className="mt-3 space-y-2">{overview.incidents.slice(0, 3).map((incident) => <div key={incident.id} className="text-sm leading-6 text-red-950/65"><span className="font-semibold text-red-950">{incident.title}.</span> {incident.summary}</div>)}</div></section>}
      </main>

      <nav className="fixed inset-x-3 bottom-3 z-40 grid grid-cols-4 rounded-[1.45rem] border border-black/10 bg-white/90 p-1.5 shadow-[0_18px_60px_rgba(0,0,0,.15)] backdrop-blur-xl md:hidden">
        <BottomNav href="/" label="Home" icon={Home} active />
        <BottomNav href="#pauli" label="Pauli" icon={Sparkles} />
        <BottomNav href="/missions" label="Work" icon={Activity} />
        <BottomNav href="/lounge" label="World" icon={Radio} />
      </nav>
    </div>
  );
}

function PauliOrb({ active }: { active: boolean }) {
  return <div className="pauli-orb-wrap" aria-label={active ? 'Pauli is active' : 'Pauli is ready'}><span className="pauli-ring" /><span className="pauli-ring ring-two" /><span className="pauli-orb" />{active && <span className="pauli-signal" />}</div>;
}

function TopNav({ href, label, active = false }: { href: string; label: string; active?: boolean }) {
  return <Link href={href} className={`pressable rounded-full px-4 py-2 text-sm font-semibold ${active ? 'bg-[#171714] text-white shadow-sm' : 'text-black/45 hover:bg-white/70 hover:text-black'}`}>{label}</Link>;
}

function BottomNav({ href, label, icon: Icon, active = false }: { href: string; label: string; icon: any; active?: boolean }) {
  return <Link href={href} className={`pressable flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[10px] font-semibold ${active ? 'bg-[#171714] text-white' : 'text-black/45 active:bg-black/[0.04]'}`}><Icon className="h-4 w-4" />{label}</Link>;
}

function SectionHeader({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle: string }) {
  return <div><div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/35">{eyebrow}</div><h2 className="mt-2 text-2xl font-semibold tracking-[-0.045em] md:text-[1.75rem]">{title}</h2><p className="mt-2 max-w-xl text-sm leading-6 text-black/45">{subtitle}</p></div>;
}

function MoneyCard({ label, value, sublabel, coverage, icon: Icon, profit = false }: { label: string; value: string; sublabel: string; coverage: string; icon: any; profit?: boolean }) {
  const warning = coverage !== 'complete';
  return <div className={`owner-card money-card ${profit ? 'money-profit' : ''} rounded-[2rem] p-6 md:p-7`}><div className="relative z-10 flex items-center justify-between"><div><div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-black/35">{label}</div><div className={`mt-1 inline-flex items-center gap-1.5 text-[10px] font-semibold ${warning ? 'text-amber-700' : 'text-emerald-700'}`}><span className={`h-1.5 w-1.5 rounded-full ${warning ? 'bg-amber-500' : 'bg-emerald-500'}`} />{sublabel}</div></div><div className="grid h-11 w-11 place-items-center rounded-full bg-[#f3f0ea]/90"><Icon className="h-4 w-4" /></div></div><div className="relative z-10 mt-8 text-4xl font-semibold tracking-[-0.06em] md:text-5xl">{value}</div><div className="relative z-10 mt-4 h-px w-full bg-black/[0.055]" /><div className="relative z-10 mt-3 text-[11px] text-black/38">{warning ? 'Pauli will not invent missing financial data.' : 'Source-qualified business data.'}</div></div>;
}

function SmallOutcome({ label, value, tone }: { label: string; value: number; tone: 'gold' | 'sage' | 'blue' }) {
  const background = tone === 'gold' ? 'bg-[#eee2ca]/75' : tone === 'sage' ? 'bg-[#dfe9d9]/78' : 'bg-[#dce8ed]/78';
  return <div className={`rounded-[1.5rem] border border-black/[0.055] ${background} p-5 shadow-sm`}><div className="text-3xl font-semibold tracking-[-0.05em]">{value}</div><div className="mt-2 text-xs font-medium text-black/43">{label}</div></div>;
}

function StateDot({ status }: { status: string }) {
  const good = ['working', 'meeting'].includes(status);
  const warning = ['recovering', 'waiting_approval'].includes(status);
  return <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ${good ? 'bg-emerald-50 text-emerald-700' : warning ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}`}>{good && <span className="state-live-dot" />}{humanize(status)}</span>;
}

function EmptyCard({ label, compact = false }: { label: string; compact?: boolean }) {
  return <div className={`${compact ? 'p-5' : 'owner-card rounded-[1.5rem] border-dashed p-5'} text-sm leading-6 text-black/40`}>{label}</div>;
}
