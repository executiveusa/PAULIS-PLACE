'use client';

import { useState, useCallback } from 'react';
import { voice, Envelope } from '@/lib/loungeApi';

// TS types for the Web Speech API (browser-only)
type SpeechRec = any;

interface UseVoiceOpts {
  onHalt?: (env: Envelope) => void;
  onAccept?: (env: Envelope) => void;
}

export function useVoiceCommand({ onHalt, onAccept }: UseVoiceOpts = {}) {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<Envelope | null>(null);
  const recRef = useState<SpeechRec | null>(null);

  const start = useCallback(() => {
    if (typeof window === 'undefined') return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('Web Speech API not supported in this browser. Try Chrome.');
      return;
    }
    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = 'en-US';

    rec.onresult = async (ev: any) => {
      const text = ev.results?.[0]?.[0]?.transcript || '';
      setTranscript(text);
      setListening(false);
      try {
        const env = await voice.command(text);
        setLastResponse(env);
        if (env.halt || env.judge_verdict === 'halt') onHalt?.(env);
        else onAccept?.(env);
      } catch (e: any) {
        setError(e.message || String(e));
      }
    };
    rec.onerror = (e: any) => {
      setError(`speech error: ${e?.error || 'unknown'}`);
      setListening(false);
    };
    rec.onend = () => setListening(false);

    recRef[1](rec);
    rec.start();
    setListening(true);
    setError(null);
  }, [onHalt, onAccept, recRef]);

  const stop = useCallback(() => {
    const r = recRef[0];
    if (r) r.stop();
    setListening(false);
  }, [recRef]);

  return { listening, transcript, error, lastResponse, start, stop };
}