'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import { lounge as loungeApi, Envelope } from '@/lib/loungeApi';
import { useVoiceCommand } from './useVoiceCommand';
import { demo, AVATAR_ROSTER } from '@/lib/demo';

// Three.js must be client-side only
const ThreeScene = dynamic(() => import('./ThreeScene'), { ssr: false });

const INTENT_TIPS: Record<string, string> = {
  who_owns:     "say \"who owns this place\"",
  whats_hot:    "say \"what's hot tonight\"",
  how_is_money: "say \"how's the money\"",
  post_that:    "say \"post that\"",
  whos_paying:  "say \"who's paying\" or \"confirmation\"",
  tell_about:   "say \"tell me about the new drop\"",
  cut_it:       "say \"cut it\" — Niko roasts",
  human_moment: "say \"human moment\" — Mira cutaway",
};

const DEFAULT_STATE = {
  lounge: "Paulie's Place",
  setting: 'Seattle 2056 · jazz lounge · 3D observable world',
  avatars: AVATAR_ROSTER.map((a) => ({ ...a })),
  schedule_cue: 'the house band tunes up…',
};

export default function LoungeClient() {
  const [state, setState] = useState(DEFAULT_STATE);
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [scenes, setScenes] = useState<Envelope[]>([]);
  const [speaker, setSpeaker] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let demoFeed: ReturnType<typeof setInterval> | null = null;

    loungeApi.state().then((s) => {
      if (cancelled) return;
      if (s && s.avatars && s.avatars.length) setState(s);
      setBackendUp(true);
    }).catch(() => {
      if (cancelled) return;
      setBackendUp(false);
      setState(DEFAULT_STATE);
      // Local ambient feed so the lounge never feels dead
      demoFeed = setInterval(() => {
        demo.scenes(1).then((r) => {
          setScenes((prev) => [r.scenes[0], ...prev].slice(0, 12));
        });
      }, 2600);
    });

    loungeApi.scenes(12).then((r) => setScenes(r.scenes)).catch(() => {});

    const wsBase = process.env.NEXT_PUBLIC_LOUNGE_WS_URL || 'ws://localhost:8000/ws';
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsBase);
      ws.onmessage = (m) => {
        try {
          const data = JSON.parse(m.data);
          if (data?.type === 'event' && data.envelope?.route?.startsWith('R-02')) {
            setScenes((s) => [data.envelope, ...s].slice(0, 12));
            setBackendUp(true);
          }
          if (data?.type === 'event' && data.envelope?.route?.startsWith('R-04')) {
            setScenes((s) => [data.envelope, ...s].slice(0, 12));
            setSpeaker(data.envelope?.body?.target_avatar);
            setTimeout(() => setSpeaker(null), 3500);
          }
        } catch {}
      };
    } catch {}

    return () => {
      cancelled = true;
      if (demoFeed) clearInterval(demoFeed);
      ws?.close();
    };
  }, []);

  const onAccept = (env: Envelope) => {
    setScenes((s) => [env, ...s].slice(0, 12));
    const spk = env?.body?.target_avatar;
    if (spk) {
      setSpeaker(spk);
      setTimeout(() => setSpeaker(null), 3500);
    }
  };

  const { listening, transcript, error, lastResponse, start, stop } = useVoiceCommand({ onAccept });

  return (
    <div className="min-h-screen bg-[#0A0714] text-[#E6DCFF]">
      <header className="px-8 py-6 border-b border-[#2A1F3D] flex items-center justify-between">
        <div>
          <h1 className="text-2xl italic font-serif text-[#FF6432]">Paulie's Place</h1>
          <p className="text-sm text-[#6B5F8A]">Seattle 2056 · jazz lounge · 3D observable world</p>
        </div>
        <div className="flex items-center gap-3">
          {backendUp === false && (
            <span className="text-xs text-[#C8AA32] border border-[#C8AA32]/40 rounded-full px-3 py-1">
              live studio demo — backend offline
            </span>
          )}
          <button
            onClick={listening ? stop : start}
            className={`px-5 py-2 rounded-lg text-sm font-semibold transition-colors
              ${listening ? 'bg-[#FF6432] text-white animate-pulse' : 'bg-[#C8AA32] text-[#0A0714]'}`}
          >
            {listening ? 'Listening… (tap to stop)' : 'Hold to speak (Jarvis)'}
          </button>
        </div>
      </header>

      {error && (
        <div className="px-8 py-3 bg-[#3A0A0A] border-b border-[#E05A5A] text-[#E05A5A] text-sm">
          {error}
        </div>
      )}

      <main className="grid lg:grid-cols-[1fr_360px] gap-6 px-8 py-6">
        <section className="space-y-4">
          <ThreeScene
            avatars={state.avatars}
            speakingAvatarId={speaker}
            sceneCue={state.schedule_cue}
          />

          <div className="rounded-2xl border border-[#2A1F3D] bg-[#140F1E] p-5">
            <h2 className="font-serif italic text-[#FF6432] mb-3">Try saying</h2>
            <div className="grid grid-cols-2 gap-2 text-xs text-[#A080E0]">
              {Object.entries(INTENT_TIPS).map(([k, v]) => (
                <div key={k} className="px-3 py-2 bg-[#1A1230] rounded-md">{v}</div>
              ))}
            </div>
          </div>

          {transcript && (
            <div className="rounded-md border border-[#2A1F3D] bg-[#0F3A2A] px-4 py-3 text-[#4DC99A]">
              <span className="opacity-70">You said: </span>{transcript}
            </div>
          )}
          {lastResponse?.halt && (
            <div className="rounded-md border border-[#E05A5A] bg-[#3A0A0A] px-4 py-3 text-[#E05A5A]">
              SAFETY_JUDGE halted: {lastResponse?.body?.reason || 'unknown'}
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-[#2A1F3D] bg-[#140F1E] p-5">
            <h2 className="font-serif italic text-[#FF6432] mb-3">Live scenes feed</h2>
            <ul className="space-y-2 text-xs max-h-[460px] overflow-y-auto">
              {scenes.length === 0 && <li className="text-[#6B5F8A]">house lights up… be the first seed</li>}
              {scenes.map((s) => (
                <li key={s.event_id + s.ts} className="px-3 py-2 bg-[#0A0714] rounded">
                  <div className="text-[#C8AA32] font-mono text-[10px] tracking-wider">{s.route} · {s.stage}</div>
                  <div className="text-[#E6DCFF] mt-1">
                    {s.body?.response_text || s.body?.lounge_scene_intent ||
                      s.body?.celebration_intent || JSON.stringify(s.body).slice(0, 140)}
                  </div>
                  <div className="text-[#6B5F8A] mt-1 text-[10px]">{s.ts}</div>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </main>
    </div>
  );
}