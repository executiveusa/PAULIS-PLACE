'use client';

import { AlertTriangle, CheckCircle2, CircleDollarSign, Scale } from 'lucide-react';
import type { PortfolioDecision, PortfolioPerspective } from '@/lib/loungeApi';

const ROLE_ORDER = [
  ['operator', 'Operator'],
  ['cfo', 'CFO'],
  ['consolidator', 'Consolidator'],
  ['red_team', 'Red Team'],
  ['evidence_judge', 'Evidence Judge'],
  ['mission_guardian', 'Mission Guardian'],
  ['opportunity_advocate', 'Opportunity Advocate'],
] as const;

function asList(value?: string[] | string | null) {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function PerspectiveCard({ label, perspective, model }: { label: string; perspective?: PortfolioPerspective; model?: string }) {
  if (!perspective) {
    return (
      <div className="border border-white/10 bg-black/20 p-4">
        <div className="text-[10px] uppercase tracking-[0.22em] text-stone-500">{label}</div>
        <div className="mt-3 text-xs text-stone-600">No persisted perspective.</div>
      </div>
    );
  }

  return (
    <div className="border border-white/10 bg-black/20 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="text-[10px] uppercase tracking-[0.22em] text-amber-100/60">{label}</div>
        {model && <span className="font-mono text-[9px] text-stone-700">{model}</span>}
      </div>
      {perspective.position && <p className="mt-3 text-sm leading-6 text-stone-200">{perspective.position}</p>}
      {perspective.recommendation && (
        <div className="mt-3 border-l border-emerald-300/30 pl-3 text-xs leading-5 text-emerald-100/70">
          {perspective.recommendation}
        </div>
      )}
      {!!perspective.risks?.length && (
        <div className="mt-4">
          <div className="text-[9px] uppercase tracking-wider text-red-300/60">Risks</div>
          <ul className="mt-2 space-y-1 text-xs leading-5 text-stone-400">
            {perspective.risks.map((risk) => <li key={risk}>• {risk}</li>)}
          </ul>
        </div>
      )}
      {!!perspective.assumptions?.length && (
        <div className="mt-4">
          <div className="text-[9px] uppercase tracking-wider text-stone-600">Assumptions</div>
          <ul className="mt-2 space-y-1 text-xs leading-5 text-stone-500">
            {perspective.assumptions.map((item) => <li key={item}>• {item}</li>)}
          </ul>
        </div>
      )}
      {perspective.stop_condition && (
        <div className="mt-4 text-[10px] leading-5 text-red-200/60">Stop: {perspective.stop_condition}</div>
      )}
    </div>
  );
}

export default function CouncilChamber({ decisions }: { decisions: PortfolioDecision[] }) {
  if (decisions.length === 0) {
    return (
      <div className="grid min-h-[520px] place-items-center border border-white/10 bg-[#0e0e0e] p-8 text-center">
        <div className="max-w-xl">
          <Scale className="mx-auto h-8 w-8 text-stone-700" />
          <h2 className="mt-5 text-lg font-semibold text-white">Council Chamber</h2>
          <p className="mt-2 text-sm leading-6 text-stone-500">
            No persisted Pauliverse portfolio deliberations exist yet. This view never invents a council result. A decision appears here only after the backend records a real seven-perspective deliberation receipt.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {decisions.map((decision) => {
        const synthesis = decision.synthesis || {};
        const ownerGates = asList(synthesis.owner_gate);
        return (
          <article key={decision.decision_id} className="border border-white/10 bg-[#0e0e0e]">
            <header className="border-b border-white/10 p-5 lg:p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="max-w-4xl">
                  <div className="text-[10px] uppercase tracking-[0.3em] text-amber-100/60">Council Chamber · {decision.status}</div>
                  <h2 className="mt-3 text-xl font-semibold text-white">{decision.question}</h2>
                  <p className="mt-2 text-sm leading-6 text-stone-400">{decision.proposal}</p>
                </div>
                <div className="text-right text-[10px] leading-5 text-stone-600">
                  <div>{decision.ts}</div>
                  <div>{decision.decision_id}</div>
                </div>
              </div>
            </header>

            <div className="grid gap-4 p-5 lg:grid-cols-2 lg:p-6 xl:grid-cols-3">
              {ROLE_ORDER.map(([key, label]) => (
                <PerspectiveCard key={key} label={label} perspective={decision.perspectives?.[key]} model={decision.models?.[key]} />
              ))}
            </div>

            <section className="border-t border-white/10 p-5 lg:p-6">
              <div className="flex flex-wrap items-center gap-3">
                <span className="inline-flex items-center gap-2 border border-emerald-300/20 px-3 py-1.5 text-[10px] uppercase tracking-wider text-emerald-200">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Hermes synthesis: {synthesis.decision || 'UNRESOLVED'}
                </span>
                {synthesis.financial_route && (
                  <span className="inline-flex items-center gap-2 border border-amber-300/20 px-3 py-1.5 text-[10px] uppercase tracking-wider text-amber-100/70">
                    <CircleDollarSign className="h-3.5 w-3.5" /> {synthesis.financial_route}
                  </span>
                )}
                {decision.synthesis_model && <span className="font-mono text-[10px] text-stone-700">judge: {decision.synthesis_model}</span>}
              </div>

              {synthesis.reasoning && <p className="mt-4 max-w-5xl text-sm leading-6 text-stone-300">{synthesis.reasoning}</p>}

              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div className="border border-white/10 p-4">
                  <div className="text-[10px] uppercase tracking-wider text-stone-600">Agreements</div>
                  {synthesis.agreements?.length ? (
                    <ul className="mt-3 space-y-1 text-xs leading-5 text-stone-400">{synthesis.agreements.map((item) => <li key={item}>• {item}</li>)}</ul>
                  ) : <p className="mt-3 text-xs text-stone-700">None recorded.</p>}
                </div>
                <div className="border border-red-400/15 p-4">
                  <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-red-200/60"><AlertTriangle className="h-3.5 w-3.5" />Material dissent</div>
                  {synthesis.disagreements?.length ? (
                    <ul className="mt-3 space-y-1 text-xs leading-5 text-stone-400">{synthesis.disagreements.map((item) => <li key={item}>• {item}</li>)}</ul>
                  ) : <p className="mt-3 text-xs text-stone-700">No disagreement recorded.</p>}
                </div>
              </div>

              <div className="mt-5 grid gap-4 lg:grid-cols-3">
                <div><div className="text-[10px] uppercase tracking-wider text-stone-600">Smallest test</div><p className="mt-2 text-xs leading-5 text-stone-400">{synthesis.smallest_test || 'Not recorded'}</p></div>
                <div><div className="text-[10px] uppercase tracking-wider text-stone-600">Next action</div><p className="mt-2 text-xs leading-5 text-stone-400">{synthesis.next_action || 'Not recorded'}</p></div>
                <div><div className="text-[10px] uppercase tracking-wider text-stone-600">Evidence receipt</div><p className="mt-2 break-all font-mono text-[10px] leading-5 text-stone-600">{decision.evidence_ref || decision._evidence_ref || 'Not recorded'}</p></div>
              </div>

              {!!ownerGates.length && (
                <div className="mt-5 border border-amber-300/20 bg-amber-300/5 p-4">
                  <div className="text-[10px] uppercase tracking-wider text-amber-200">Owner gate</div>
                  <ul className="mt-2 space-y-1 text-xs leading-5 text-amber-100/70">{ownerGates.map((gate) => <li key={gate}>• {gate}</li>)}</ul>
                </div>
              )}
            </section>
          </article>
        );
      })}
    </div>
  );
}
