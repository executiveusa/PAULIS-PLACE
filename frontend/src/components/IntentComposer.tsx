'use client';

import { FormEvent, useMemo, useRef, useState } from 'react';
import { Mic, MicOff, Send, PhoneCall, Sparkles } from 'lucide-react';
import { api, MissionCreateResponse } from '@/lib/api';

interface Props {
  onCreated?: (mission: MissionCreateResponse) => void;
  compact?: boolean;
}

function inferLanguage(text: string): 'en' | 'es-MX' | 'mixed' {
  const lower = text.toLowerCase();
  const spanish = /\b(quiero|necesito|haz|crea|busca|dime|para|con|que|una|un|los|las|por favor|llámame|llama)\b/.test(lower);
  const english = /\b(i|want|need|build|create|find|tell|call|make|the|with|for|please)\b/.test(lower);
  if (spanish && english) return 'mixed';
  return spanish ? 'es-MX' : 'en';
}

export function IntentComposer({ onCreated, compact = false }: Props) {
  const [intent, setIntent] = useState('');
  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const recognitionRef = useRef<any>(null);
  const language = useMemo(() => inferLanguage(intent), [intent]);

  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessage('Live browser speech is not available on this device. Type your intent or use the phone channel.');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = language === 'es-MX' ? 'es-MX' : 'en-US';
    recognition.onresult = (event: any) => {
      let text = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) text += event.results[i][0].transcript;
      setIntent(text.trim());
    };
    recognition.onerror = () => {
      setListening(false);
      setMessage('I could not hear that clearly. Try again or type the intent.');
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    setListening(true);
    setMessage('');
    recognition.start();
  };

  const stopListening = () => {
    recognitionRef.current?.stop?.();
    setListening(false);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const clean = intent.trim();
    if (!clean) return;
    setBusy(true);
    setMessage('');
    try {
      const mission = await api.controlPlane.createMission({
        title: clean.length > 72 ? `${clean.slice(0, 69)}…` : clean,
        intent: clean,
        requested_outcome: clean,
        language: inferLanguage(clean),
        autonomous_budget_cents: 1000,
      });
      setMessage(`Mission accepted. Pauli is assembling the team.`);
      setIntent('');
      onCreated?.(mission);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Mission Control is not reachable yet.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`pauli-panel ${compact ? 'p-4' : 'p-5 md:p-7'}`}>
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <div className="eyebrow">Talk to Pauli</div>
          <h2 className={`${compact ? 'text-xl' : 'text-2xl md:text-3xl'} font-semibold tracking-tight mt-1`}>What do you want done?</h2>
          {!compact && <p className="text-sm text-stone-400 mt-2 max-w-2xl">Say the outcome in plain English or Mexican Spanish. Pauli handles the technical steps, team, tools and computers underneath.</p>}
        </div>
        <div className="hidden sm:flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-stone-500">
          <span className="status-dot status-live" /> {language === 'es-MX' ? 'MX Spanish' : language === 'mixed' ? 'Mixed language' : 'English'}
        </div>
      </div>

      <form onSubmit={submit} className="relative">
        <textarea
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          placeholder="Example: Find a nonprofit that needs a better website, build the preview, and call me when it is ready."
          rows={compact ? 2 : 3}
          className="w-full resize-none rounded-2xl border border-white/10 bg-black/35 px-4 py-4 pr-28 text-[15px] md:text-base leading-relaxed text-stone-100 placeholder:text-stone-600 outline-none transition focus:border-white/30 focus:bg-black/45"
        />
        <div className="absolute right-3 bottom-3 flex items-center gap-2">
          <button type="button" onClick={listening ? stopListening : startListening} aria-label={listening ? 'Stop listening' : 'Speak intent'}
            className={`h-10 w-10 rounded-full grid place-items-center border transition ${listening ? 'bg-red-500 text-white border-red-400 animate-pulse' : 'bg-white/5 border-white/10 text-stone-300 hover:bg-white/10'}`}>
            {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          </button>
          <button type="submit" disabled={busy || !intent.trim()} aria-label="Send mission"
            className="h-10 px-4 rounded-full bg-stone-100 text-stone-950 font-semibold text-sm flex items-center gap-2 disabled:opacity-30 hover:bg-white transition">
            {busy ? <Sparkles className="w-4 h-4 animate-pulse" /> : <Send className="w-4 h-4" />}
            <span className="hidden md:inline">Give it to Pauli</span>
          </button>
        </div>
      </form>

      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-stone-500">
        <span>{listening ? 'Listening… you can stop me anytime.' : message || 'Zero-cost reversible work runs automatically. Consequential actions still stop for your approval.'}</span>
        <span className="hidden md:flex items-center gap-1.5 whitespace-nowrap"><PhoneCall className="w-3.5 h-3.5" /> phone + web + WhatsApp</span>
      </div>
    </div>
  );
}
