'use client';

import { Canvas } from '@react-three/fiber';
import { Line, OrbitControls } from '@react-three/drei';
import { useMemo, useState } from 'react';
import { ExternalLink, Search } from 'lucide-react';
import type { PauliverseEdge, PauliverseNode, PauliverseSnapshot } from '@/lib/pauliverseApi';

const DISTRICT_ORDER = [
  'BUSINESS',
  'STORY_IP',
  'AGENTS_CAPABILITIES',
  'INFRASTRUCTURE',
  'SOCIAL_PURPOSE',
  'ARCHIVE',
];

const DISTRICT_RADIUS: Record<string, number> = {
  BUSINESS: 4.2,
  STORY_IP: 6.1,
  AGENTS_CAPABILITIES: 7.7,
  INFRASTRUCTURE: 9.2,
  SOCIAL_PURPOSE: 10.7,
  ARCHIVE: 12.2,
};

const STATUS_COLOR: Record<string, string> = {
  HEALTHY: '#4ade80',
  ACTIVE: '#93c5fd',
  TESTING: '#facc15',
  NEEDS_APPROVAL: '#fb923c',
  BLOCKED: '#f87171',
  DEGRADED: '#fca5a5',
  ARCHIVED: '#78716c',
};

function buildPositions(nodes: PauliverseNode[]) {
  const grouped = new Map<string, PauliverseNode[]>();
  for (const node of nodes) {
    const district = node.district || 'ARCHIVE';
    grouped.set(district, [...(grouped.get(district) || []), node]);
  }

  const positions: Record<string, [number, number, number]> = {};
  for (const [district, districtNodes] of grouped.entries()) {
    const radius = DISTRICT_RADIUS[district] || 12.2;
    districtNodes.forEach((node, index) => {
      const angle = (Math.PI * 2 * index) / Math.max(districtNodes.length, 1) + DISTRICT_ORDER.indexOf(district) * 0.4;
      const y = node.type === 'AGENT' ? 1.6 : node.type === 'OPPORTUNITY' ? 0.9 : node.type === 'DEPLOYMENT' ? -1.0 : 0;
      positions[node.id] = [Math.cos(angle) * radius, y, Math.sin(angle) * radius];
    });
  }
  return positions;
}

function NodeSphere({ node, position, selected, onSelect }: {
  node: PauliverseNode;
  position: [number, number, number];
  selected: boolean;
  onSelect: () => void;
}) {
  const color = STATUS_COLOR[node.status || ''] || '#d6d3d1';
  const scale = node.type === 'REPOSITORY' ? 0.54 : node.type === 'AGENT' ? 0.46 : 0.38;

  return (
    <mesh position={position} scale={selected ? scale * 1.45 : scale} onClick={(event) => { event.stopPropagation(); onSelect(); }}>
      <sphereGeometry args={[1, 24, 24]} />
      <meshStandardMaterial color={color} emissive={selected ? color : '#000000'} emissiveIntensity={selected ? 0.55 : 0.08} roughness={0.35} />
    </mesh>
  );
}

function EdgeLine({ edge, positions }: { edge: PauliverseEdge; positions: Record<string, [number, number, number]> }) {
  const source = positions[edge.source];
  const target = positions[edge.target];
  if (!source || !target) return null;
  return (
    <Line
      points={[source, target]}
      color={edge.active ? '#c8aa32' : '#3f3f46'}
      transparent
      opacity={edge.active ? 0.72 : 0.25}
      lineWidth={edge.active ? 1.25 : 0.6}
    />
  );
}

export default function CommandWorld({ snapshot }: { snapshot: PauliverseSnapshot }) {
  const [selectedId, setSelectedId] = useState<string>(snapshot.nodes[0]?.id || '');
  const [query, setQuery] = useState('');
  const positions = useMemo(() => buildPositions(snapshot.nodes), [snapshot.nodes]);
  const selected = snapshot.nodes.find((node) => node.id === selectedId) || snapshot.nodes[0];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return snapshot.nodes;
    return snapshot.nodes.filter((node) =>
      [node.name, node.repo, node.status, node.authority, node.summary, node.type]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(needle)),
    );
  }, [query, snapshot.nodes]);
  const visibleIds = new Set(filtered.map((node) => node.id));

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <div className="overflow-hidden border border-white/10 bg-black">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
          <div>
            <div className="text-[10px] uppercase tracking-[0.28em] text-amber-100/60">Pauliverse Command World</div>
            <div className="mt-1 text-xs text-stone-500">{snapshot.nodes.length} real nodes · {snapshot.edges.length} provenance-backed relationships</div>
          </div>
          <label className="flex items-center gap-2 border border-white/10 bg-[#0e0e0e] px-3 py-2 text-xs text-stone-400">
            <Search className="h-3.5 w-3.5" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Find repo, agent, opportunity…"
              className="w-52 bg-transparent outline-none placeholder:text-stone-700"
            />
          </label>
        </div>
        <div className="h-[620px]">
          <Canvas camera={{ position: [0, 12, 19], fov: 48 }} onPointerMissed={() => setSelectedId('')}>
            <color attach="background" args={['#050505']} />
            <fog attach="fog" args={['#050505', 18, 40]} />
            <ambientLight intensity={0.75} />
            <pointLight position={[0, 7, 0]} intensity={28} color="#c8aa32" distance={24} />
            {snapshot.edges
              .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
              .map((edge) => <EdgeLine key={edge.id} edge={edge} positions={positions} />)}
            {filtered.map((node) => (
              <NodeSphere
                key={node.id}
                node={node}
                position={positions[node.id] || [0, 0, 0]}
                selected={node.id === selectedId}
                onSelect={() => setSelectedId(node.id)}
              />
            ))}
            <OrbitControls enableDamping dampingFactor={0.08} minDistance={6} maxDistance={32} />
          </Canvas>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-white/10 px-4 py-3 text-[10px] uppercase tracking-wider text-stone-500">
          {Object.entries(STATUS_COLOR).map(([status, color]) => (
            <span key={status} className="flex items-center gap-2"><i className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />{status.replaceAll('_', ' ')}</span>
          ))}
        </div>
      </div>

      <aside className="border border-white/10 bg-[#0e0e0e] p-5">
        {!selected ? (
          <div className="text-sm text-stone-500">Select a node to inspect its authority, evidence and current action.</div>
        ) : (
          <div className="space-y-5">
            <div>
              <div className="text-[10px] uppercase tracking-[0.28em] text-stone-600">{selected.type}</div>
              <h2 className="mt-2 text-xl font-semibold text-white">{selected.name}</h2>
              <div className="mt-2 flex flex-wrap gap-2 text-[10px] uppercase tracking-wider">
                <span className="border border-white/10 px-2 py-1 text-stone-300">{selected.status || 'UNKNOWN'}</span>
                <span className="border border-white/10 px-2 py-1 text-stone-500">{selected.disposition || 'UNCLASSIFIED'}</span>
              </div>
            </div>

            <dl className="space-y-4 text-xs">
              <div><dt className="uppercase tracking-wider text-stone-600">Authority</dt><dd className="mt-1 leading-5 text-stone-300">{selected.authority || 'Not recorded'}</dd></div>
              <div><dt className="uppercase tracking-wider text-stone-600">Health</dt><dd className="mt-1 leading-5 text-stone-300">{selected.health || 'Not recorded'}</dd></div>
              <div><dt className="uppercase tracking-wider text-stone-600">Summary</dt><dd className="mt-1 leading-5 text-stone-300">{selected.summary || 'Not recorded'}</dd></div>
            </dl>

            {!!selected.active_missions?.length && (
              <div><div className="text-[10px] uppercase tracking-wider text-stone-600">Active missions</div><div className="mt-2 space-y-1 text-xs text-amber-100/70">{selected.active_missions.map((mission) => <div key={mission}>{mission}</div>)}</div></div>
            )}
            {!!selected.financial_signals?.length && (
              <div><div className="text-[10px] uppercase tracking-wider text-stone-600">Financial signals</div><div className="mt-2 flex flex-wrap gap-2">{selected.financial_signals.map((signal) => <span key={signal} className="border border-emerald-400/20 px-2 py-1 text-[10px] text-emerald-200">{signal}</span>)}</div></div>
            )}
            {!!selected.owner_approvals_required?.length && (
              <div className="border border-amber-300/20 bg-amber-300/5 p-3"><div className="text-[10px] uppercase tracking-wider text-amber-200">Owner gates</div><ul className="mt-2 space-y-1 text-xs leading-5 text-amber-100/70">{selected.owner_approvals_required.map((gate) => <li key={gate}>• {gate}</li>)}</ul></div>
            )}
            {!!selected.evidence_refs?.length && (
              <div><div className="text-[10px] uppercase tracking-wider text-stone-600">Evidence</div><ul className="mt-2 space-y-2 text-xs leading-5 text-stone-400">{selected.evidence_refs.map((ref) => <li key={ref}>{ref}</li>)}</ul></div>
            )}

            {(selected.deployment_url || selected.repo) && (
              <div className="flex flex-wrap gap-2 border-t border-white/10 pt-4">
                {selected.deployment_url && <a href={selected.deployment_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 border border-white/10 px-3 py-2 text-xs text-stone-300 hover:text-white">Open deployment <ExternalLink className="h-3 w-3" /></a>}
                {selected.repo && <a href={`https://github.com/${selected.repo}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 border border-white/10 px-3 py-2 text-xs text-stone-300 hover:text-white">Open repo <ExternalLink className="h-3 w-3" /></a>}
              </div>
            )}

            <div className="border-t border-white/10 pt-4 text-[10px] leading-5 text-stone-600">
              Source: {selected.provenance?.source_ref || snapshot.source}<br />
              Observed: {selected.provenance?.observed_at || snapshot.generated_at}<br />
              Confidence: {selected.provenance?.confidence ?? 'n/a'}
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}
