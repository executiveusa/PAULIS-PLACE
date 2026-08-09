'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import {
  ArrowUpRight,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Map,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
} from 'lucide-react';
import { api, ControlPlaneStatus, Mission } from '@/lib/api';
import { IntentComposer } from '@/components/IntentComposer';

const places = [
  { name: "Pauli's Place", sub: 'Executive room', href: '/lounge' },
  { name: "Max's", sub: 'Client workspace', href: '/lounge' },
  { name: 'The Factory', sub: 'Products + software', href: '/products' },
  { name: 'The Library', sub: 'Research', href: '/research' },
];

export default function HomePage() {
  const [status, setStatus] = useState<ControlPlaneStatus | null>(null);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [error, setError] = useState('');

  const refresh = async () => {
    try {
      const [nextStatus, nextMissions] = await Promise.all([
        api.controlPlane.status(),
        api.controlPlane.missions('paulis-place', 6),
      ]);
      setStatus(nextStatus);
      setMissions(nextMissions.missions);
      setError('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Mission Control is unavailable.');
    }
  };

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 15000);
    return () => clearInterval(timer);
  }, []);

  const live = status?.status === 'ready';
  const active = useMemo(() => missions.filter((m) => !['CLOSED','FAILED','CANCELLED'].includes(m.status)), [missions]);

  return (
    <div className="min-h-screen noir-grid">
      <header className="px-4 pt-5 md:px-8 md:pt-8 lg:px-10 max-w-[1500px] mx-auto">
        <div className="flex items-center justify-between gap-4 mb-6 md:mb-8">
          <div>
            <div className="eyebrow">Sunday at the house</div>
            <h1 className="text-2xl md:text-3xl font-semibold tracking-[-0.035em] mt-1">What needs to get done?</h1>
          </div>
          <Link href="/lounge" className="shrink-0 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-2 text-xs text-stone-300 hover:bg-white/[0.08] transition">
            <Map className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Enter</span> Pauli's World
          </Link>
        </div>

        <IntentComposer onCreated={() => setTimeout(refresh, 250)} />
      </header>

      <main className="px-4 py-5 md:px-8 md:py-7 lg:px-10 max-w-[1500px] mx-auto space-y-5">
        {error && (
          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/[0.05] p-4 flex items-start gap-3 text-sm text-amber-100/80">
            <CircleAlert className="w-4 h-4 mt-0.5 shrink-0" />
            <div><strong className="text-amber-100">Mission Control is not connected yet.</strong><div className="text-amber-100/55 mt-1">{error}</div></div>
          </div>
        )}

        <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <SignalCard label="House" value={live ? 'Online' : status?.status?.replaceAll('_', ' ') || 'Checking'} icon={live ? CheckCircle2 : Clock3} live={live} />
          <SignalCard label="Agents" value={String(status?.counts.agents ?? 0)} note="registered" icon={Users} />
          <SignalCard label="Active missions" value={String(status?.counts.missions ?? active.length)} note="in motion" icon={Workflow} />
          <SignalCard label="Needs you" value={String(status?.counts.approvals_pending ?? 0)} note="approvals" icon={ShieldCheck} warn={(status?.counts.approvals_pending ?? 0) > 0} />
        </section>

        <section className="grid lg:grid-cols-[1.25fr_.75fr] gap-5">
          <div className="pauli-panel p-5 md:p-6 min-h-[320px]">
            <div className="flex items-center justify-between gap-4 mb-5">
              <div>
                <div className="eyebrow">Live work</div>
                <h2 className="text-xl font-semibold mt-1">What the crew is doing</h2>
              </div>
              <Link href="/missions" className="text-xs text-stone-500 hover:text-stone-200 flex items-center gap-1">All missions <ArrowUpRight className="w-3.5 h-3.5" /></Link>
            </div>

            {missions.length === 0 ? (
              <div className="h-[220px] rounded-2xl border border-dashed border-white/10 grid place-items-center text-center px-6">
                <div>
                  <Sparkles className="w-5 h-5 text-stone-600 mx-auto mb-3" />
                  <p className="text-sm text-stone-400">No real missions are recorded yet.</p>
                  <p className="text-xs text-stone-600 mt-1">Tell Pauli what you want done above. This screen will only show work that actually exists.</p>
                </div>
              </div>
            ) : (
              <div className="space-y-2.5">
                {missions.map((mission) => <MissionRow key={mission.id} mission={mission} />)}
              </div>
            )}
          </div>

          <div className="pauli-panel p-5 md:p-6">
            <div className="eyebrow">Places</div>
            <h2 className="text-xl font-semibold mt-1 mb-5">Where the work lives</h2>
            <div className="space-y-2.5">
              {places.map((place, index) => (
                <Link key={place.name} href={place.href} className="group flex items-center justify-between gap-4 rounded-xl border border-white/[0.07] bg-black/25 p-3.5 hover:bg-white/[0.045] hover:border-white/15 transition">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-9 w-9 rounded-lg grid place-items-center border border-white/[0.08] bg-white/[0.025] text-[11px] font-semibold text-stone-500">0{index + 1}</div>
                    <div className="min-w-0"><div className="text-sm font-medium truncate">{place.name}</div><div className="text-[11px] text-stone-600 mt-0.5 truncate">{place.sub}</div></div>
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-stone-700 group-hover:text-stone-300 transition" />
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="pauli-card px-4 py-3.5 md:px-5 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs text-stone-500">
          <div className="flex items-center gap-2"><span className={`status-dot ${status?.providers.agentforge?.status === 'ready' ? 'status-live' : 'status-warn'}`} />AgentForge: {status?.providers.agentforge?.status || 'checking'}</div>
          <div className="flex items-center gap-2"><span className={`status-dot ${status?.providers.composio?.status === 'ready' ? 'status-live' : 'status-warn'}`} />Composio: {status?.providers.composio?.status || 'checking'}</div>
          <div className="text-stone-700">No synthetic operational data on Mission Control surfaces.</div>
        </section>
      </main>
    </div>
  );
}

function SignalCard({ label, value, note, icon: Icon, live, warn }: { label: string; value: string; note?: string; icon: any; live?: boolean; warn?: boolean }) {
  return (
    <div className="pauli-card p-4 md:p-5 min-h-[116px] flex flex-col justify-between">
      <div className="flex items-center justify-between"><span className="eyebrow !tracking-[.15em]">{label}</span><Icon className="w-4 h-4 text-stone-700" /></div>
      <div className="mt-4"><div className="flex items-baseline gap-2"><span className="text-xl md:text-2xl font-semibold tracking-tight capitalize">{value}</span>{live && <span className="status-dot status-live" />}{warn && <span className="status-dot status-warn" />}</div>{note && <div className="text-[11px] text-stone-600 mt-1">{note}</div>}</div>
    </div>
  );
}

function MissionRow({ mission }: { mission: Mission }) {
  const status = mission.status.replaceAll('_', ' ').toLowerCase();
  const blocked = ['BLOCKED','FAILED','WAITING_APPROVAL'].includes(mission.status);
  return (
    <Link href="/missions" className="group grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded-xl border border-white/[0.065] bg-black/20 p-3.5 hover:bg-white/[0.04] hover:border-white/15 transition">
      <div className={`h-9 w-9 rounded-full grid place-items-center border ${blocked ? 'border-amber-500/20 bg-amber-500/5' : 'border-white/10 bg-white/[0.025]'}`}>
        {blocked ? <CircleAlert className="w-4 h-4 text-amber-400" /> : <Workflow className="w-4 h-4 text-stone-500" />}
      </div>
      <div className="min-w-0"><div className="text-sm font-medium truncate group-hover:text-white">{mission.title}</div><div className="text-[11px] text-stone-600 mt-1 capitalize">{status} · ${(mission.spent_cents / 100).toFixed(2)} spent / ${(mission.autonomous_budget_cents / 100).toFixed(2)} envelope</div></div>
      <ArrowUpRight className="w-4 h-4 text-stone-700 group-hover:text-stone-300" />
    </Link>
  );
}
