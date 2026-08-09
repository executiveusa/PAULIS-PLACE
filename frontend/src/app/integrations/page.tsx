'use client';

import { useEffect, useMemo, useState } from 'react';
import { ExternalLink, PlugZap, RefreshCw, ShieldCheck, ShieldAlert } from 'lucide-react';
import { api, ComposioSession, ComposioStatus } from '../../lib/api';

const STARTER_TOOLKITS = [
  'GMAIL', 'GOOGLECALENDAR', 'GOOGLEDRIVE', 'GITHUB', 'NOTION', 'SLACK',
  'AIRTABLE', 'HUBSPOT', 'SALESFORCE', 'LINEAR', 'TRELLO', 'DROPBOX',
];

export default function IntegrationsPage() {
  const [status, setStatus] = useState<ComposioStatus | null>(null);
  const [session, setSession] = useState<ComposioSession | null>(null);
  const [selected, setSelected] = useState<string[]>(['GMAIL', 'GOOGLECALENDAR', 'GOOGLEDRIVE', 'GITHUB', 'NOTION']);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  const tenantId = 'paulis-place';
  const actorId = 'pauli';

  async function refresh() {
    try {
      const next = await api.integrations.composioStatus();
      setStatus(next);
    } catch {
      setStatus({ provider: 'composio', configured: false, status: 'waiting_for_credentials', capabilities: [] });
    }
  }

  useEffect(() => { refresh(); }, []);

  const configured = status?.configured === true;
  const statusLabel = useMemo(() => configured ? 'Ready' : 'Needs COMPOSIO_API_KEY', [configured]);

  async function createSession() {
    setBusy(true); setMessage('');
    try {
      const next = await api.integrations.createReadSession(tenantId, actorId, selected);
      setSession(next);
      setMessage('Read-only agent session created. Connect accounts below as needed.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not create Composio session.');
    } finally { setBusy(false); }
  }

  async function connect(toolkit: string) {
    if (!session) return;
    setBusy(true); setMessage('');
    try {
      const result = await api.integrations.connectToolkit(session.session_id, toolkit, window.location.href);
      const url = String(result.redirect_url || result.link_url || '');
      if (!url) throw new Error('Composio did not return an authentication URL.');
      window.open(url, '_blank', 'noopener,noreferrer');
      setMessage(`Opened ${toolkit} authentication. Return here after approving access.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `Could not connect ${toolkit}.`);
    } finally { setBusy(false); }
  }

  function toggle(toolkit: string) {
    setSelected((current) => current.includes(toolkit)
      ? current.filter((x) => x !== toolkit)
      : [...current, toolkit]);
  }

  return (
    <div className="p-5 md:p-8 max-w-5xl mx-auto">
      <div className="flex items-start justify-between gap-4 mb-8">
        <div>
          <p className="text-xs tracking-[0.2em] uppercase text-gray-500 mb-2">Pauli Integrations Bus</p>
          <h1 className="text-3xl font-semibold">Connect the tools your agents need</h1>
          <p className="text-gray-400 mt-2 max-w-2xl">
            Pauli keeps mission authority and approvals. Composio handles app discovery, authentication and hosted MCP access.
          </p>
        </div>
        <button onClick={refresh} className="p-3 rounded-full border border-gray-800 hover:border-gray-600" aria-label="Refresh status">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <section className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 md:p-6 mb-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-white text-black flex items-center justify-center"><PlugZap className="w-5 h-5" /></div>
            <div><h2 className="font-semibold">Composio</h2><p className="text-sm text-gray-500">Broad SaaS tool discovery + auth + MCP</p></div>
          </div>
          <div className={`flex items-center gap-2 text-sm ${configured ? 'text-green-400' : 'text-amber-400'}`}>
            {configured ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
            {statusLabel}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-gray-800 bg-gray-900/60 p-5 md:p-6">
        <div className="flex items-center justify-between gap-4 mb-5">
          <div><h2 className="font-semibold">Autonomous read access</h2><p className="text-sm text-gray-500 mt-1">Agents may research connected systems. External writes still require Pauli approval policy.</p></div>
          <button disabled={!configured || busy || selected.length === 0} onClick={createSession}
            className="px-4 py-2.5 rounded-xl bg-white text-black disabled:opacity-40 text-sm font-medium">
            {busy ? 'Working…' : session ? 'Recreate session' : 'Start agent session'}
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {STARTER_TOOLKITS.map((toolkit) => {
            const active = selected.includes(toolkit);
            return (
              <button key={toolkit} onClick={() => toggle(toolkit)}
                className={`text-left p-4 rounded-xl border transition ${active ? 'border-white bg-white/10' : 'border-gray-800 bg-black/20 hover:border-gray-700'}`}>
                <div className="font-medium text-sm">{toolkit}</div>
                <div className="text-xs text-gray-500 mt-1">{active ? 'Enabled for discovery' : 'Not in this session'}</div>
              </button>
            );
          })}
        </div>

        {session && (
          <div className="mt-6 pt-5 border-t border-gray-800">
            <div className="flex items-center justify-between mb-4"><div><p className="text-sm font-medium">Session ready</p><p className="text-xs text-gray-500 font-mono mt-1">{session.session_id}</p></div><span className="text-xs rounded-full px-3 py-1 border border-green-900 text-green-400">READ ONLY</span></div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {session.toolkits.map((toolkit) => (
                <button key={toolkit} disabled={busy} onClick={() => connect(toolkit)}
                  className="flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg border border-gray-800 hover:border-gray-600 text-sm">
                  Connect {toolkit}<ExternalLink className="w-3.5 h-3.5" />
                </button>
              ))}
            </div>
          </div>
        )}

        {message && <p className="mt-5 text-sm text-gray-300 rounded-xl bg-black/30 border border-gray-800 p-3">{message}</p>}
      </section>

      <p className="text-xs text-gray-600 mt-5">Write/send/publish/call/financial actions are intentionally not exposed here. Those are created by Mission Control only after the applicable scoped approval.</p>
    </div>
  );
}
