'use client';

import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import Link from 'next/link';
import { Activity, ArrowRight, Check, Clock3, MapPin, ShieldAlert, Sparkles, X } from 'lucide-react';
import { useEffect } from 'react';
import type { PauliAgentSummary } from '@/lib/pauliControl';

export type FeedbackTone = 'neutral' | 'success' | 'warning' | 'error';

export interface PremiumFeedback {
  id: string;
  title: string;
  detail?: string;
  tone: FeedbackTone;
}

const toneIcon = {
  neutral: Sparkles,
  success: Check,
  warning: ShieldAlert,
  error: ShieldAlert,
};

export function FeedbackStack({ items, onDismiss }: { items: PremiumFeedback[]; onDismiss: (id: string) => void }) {
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!items.length) return;
    const timers = items.map((item) => window.setTimeout(() => onDismiss(item.id), item.tone === 'error' ? 7000 : 4500));
    return () => timers.forEach(window.clearTimeout);
  }, [items, onDismiss]);

  return (
    <div className="pointer-events-none fixed inset-x-3 top-3 z-[90] flex flex-col items-end gap-2 sm:left-auto sm:right-4 sm:top-4 sm:w-[23rem]" aria-live="polite" aria-atomic="false">
      <AnimatePresence initial={false}>
        {items.slice(-3).map((item) => {
          const Icon = toneIcon[item.tone];
          return (
            <motion.div
              key={item.id}
              layout
              initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -10, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.98 }}
              transition={{ type: 'spring', stiffness: 460, damping: 36, mass: 0.72 }}
              className={`pointer-events-auto w-full overflow-hidden rounded-[1.15rem] border px-3.5 py-3 shadow-[0_18px_55px_rgba(23,23,20,.16)] backdrop-blur-2xl ${
                item.tone === 'success'
                  ? 'border-emerald-900/10 bg-[#f2f8f0]/94'
                  : item.tone === 'warning'
                    ? 'border-amber-900/10 bg-[#fff7e9]/94'
                    : item.tone === 'error'
                      ? 'border-red-900/10 bg-[#fff1ed]/95'
                      : 'border-black/10 bg-white/93'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full ${item.tone === 'success' ? 'bg-emerald-100 text-emerald-800' : item.tone === 'warning' ? 'bg-amber-100 text-amber-800' : item.tone === 'error' ? 'bg-red-100 text-red-800' : 'bg-black/[0.06] text-black/65'}`}>
                  <Icon className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-semibold tracking-[-0.015em] text-[#171714]">{item.title}</div>
                  {item.detail && <div className="mt-0.5 text-[12px] leading-5 text-black/48">{item.detail}</div>}
                </div>
                <button onClick={() => onDismiss(item.id)} className="-mr-1 -mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full text-black/35 transition active:scale-90 hover:bg-black/[0.05] hover:text-black/65" aria-label="Dismiss notification">
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export function AgentDetailSheet({ agent, onClose }: { agent: PauliAgentSummary | null; onClose: () => void }) {
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!agent) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener('keydown', onKey);
    };
  }, [agent, onClose]);

  const heartbeat = agent?.last_heartbeat_at ? new Date(agent.last_heartbeat_at).toLocaleString() : 'No heartbeat recorded';

  return (
    <AnimatePresence>
      {agent && (
        <div className="fixed inset-0 z-[80] flex items-end justify-center md:items-center md:justify-end" role="dialog" aria-modal="true" aria-label={`${agent.name} agent details`}>
          <motion.button
            type="button"
            aria-label="Close agent details"
            className="absolute inset-0 bg-black/24 backdrop-blur-[2px]"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reduceMotion ? 0.1 : 0.18 }}
          />
          <motion.section
            drag={reduceMotion ? false : 'y'}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.22 }}
            onDragEnd={(_, info) => {
              if (info.offset.y > 110 || info.velocity.y > 700) onClose();
            }}
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 44, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 36, scale: 0.99 }}
            transition={{ type: 'spring', stiffness: 410, damping: 38, mass: 0.9 }}
            className="relative z-10 w-full max-w-xl overflow-hidden rounded-t-[2rem] border border-white/65 bg-[#f7f4ee]/96 text-[#171714] shadow-[0_-24px_80px_rgba(23,23,20,.2)] backdrop-blur-2xl md:mr-5 md:max-h-[calc(100vh-2.5rem)] md:w-[27rem] md:rounded-[2rem] md:shadow-[0_28px_100px_rgba(23,23,20,.25)]"
          >
            <div className="flex justify-center py-2.5 md:hidden"><span className="h-1 w-10 rounded-full bg-black/14" /></div>
            <div className="p-5 pt-2 md:p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex min-w-0 items-center gap-3.5">
                  <div className="agent-avatar grid h-12 w-12 shrink-0 place-items-center rounded-full bg-[#dfe9d9] text-sm font-bold">{agent.name.slice(0, 1)}</div>
                  <div className="min-w-0">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-black/36">Agent detail</div>
                    <h2 className="mt-1 truncate text-2xl font-semibold tracking-[-0.045em]">{agent.name}</h2>
                    <p className="mt-1 text-sm text-black/46">{agent.role.replace(/[._-]+/g, ' ')}</p>
                  </div>
                </div>
                <button onClick={onClose} className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-black/[0.05] text-black/45 transition active:scale-90 hover:bg-black/[0.08] hover:text-black" aria-label="Close agent details"><X className="h-4 w-4" /></button>
              </div>

              <div className="mt-6 grid gap-2.5">
                <DetailRow icon={Activity} label="Current state" value={agent.status.replace(/[._-]+/g, ' ')} />
                <DetailRow icon={Sparkles} label="Specialty" value={agent.specialty || 'No specialty recorded'} />
                <DetailRow icon={Clock3} label="Last heartbeat" value={heartbeat} />
                <DetailRow icon={MapPin} label="World location" value={agent.world_location_key ? agent.world_location_key.replace(/[._-]+/g, ' ') : 'No location recorded'} />
              </div>

              <div className="mt-6 rounded-[1.3rem] border border-black/[0.06] bg-white/65 p-4 text-xs leading-5 text-black/46">
                This panel shows recorded runtime state only. Controls that are not backed by the control plane are intentionally not shown.
              </div>

              <Link href="/agents" className="mt-4 flex min-h-12 items-center justify-between rounded-[1.15rem] bg-[#171714] px-4 text-sm font-semibold text-white transition active:scale-[0.985]">
                Open workforce control <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </motion.section>
        </div>
      )}
    </AnimatePresence>
  );
}

function DetailRow({ icon: Icon, label, value }: { icon: typeof Activity; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-[1.15rem] border border-black/[0.055] bg-white/58 p-3.5">
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-black/[0.045] text-black/55"><Icon className="h-3.5 w-3.5" /></div>
      <div className="min-w-0"><div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-black/32">{label}</div><div className="mt-0.5 truncate text-sm font-medium capitalize text-black/72">{value}</div></div>
    </div>
  );
}
