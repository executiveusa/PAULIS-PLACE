'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink, Search } from 'lucide-react';
import * as THREE from 'three';
import type { PauliverseNode, PauliverseSnapshot } from '@/lib/pauliverseApi';

const DISTRICT_ORDER = ['BUSINESS','STORY_IP','AGENTS_CAPABILITIES','INFRASTRUCTURE','SOCIAL_PURPOSE','ARCHIVE'];
const DISTRICT_RADIUS: Record<string, number> = { BUSINESS: 4.2, STORY_IP: 6.1, AGENTS_CAPABILITIES: 7.7, INFRASTRUCTURE: 9.2, SOCIAL_PURPOSE: 10.7, ARCHIVE: 12.2 };
const STATUS_COLOR: Record<string, number> = { HEALTHY: 0x4ade80, ACTIVE: 0x93c5fd, TESTING: 0xfacc15, NEEDS_APPROVAL: 0xfb923c, BLOCKED: 0xf87171, DEGRADED: 0xfca5a5, ARCHIVED: 0x78716c };
const STATUS_CSS: Record<string, string> = { HEALTHY: '#4ade80', ACTIVE: '#93c5fd', TESTING: '#facc15', NEEDS_APPROVAL: '#fb923c', BLOCKED: '#f87171', DEGRADED: '#fca5a5', ARCHIVED: '#78716c' };

function buildPositions(nodes: PauliverseNode[]) {
  const grouped: Record<string, PauliverseNode[]> = {};
  for (const node of nodes) {
    const district = node.district || 'ARCHIVE';
    (grouped[district] ||= []).push(node);
  }
  const positions: Record<string, [number, number, number]> = {};
  Object.entries(grouped).forEach(([district, districtNodes]) => {
    const radius = DISTRICT_RADIUS[district] || 12.2;
    districtNodes.forEach((node, index) => {
      const districtIndex = Math.max(0, DISTRICT_ORDER.indexOf(district));
      const angle = (Math.PI * 2 * index) / Math.max(districtNodes.length, 1) + districtIndex * 0.4;
      const y = node.type === 'AGENT' ? 1.6 : node.type === 'OPPORTUNITY' ? 0.9 : node.type === 'DEPLOYMENT' ? -1 : 0;
      positions[node.id] = [Math.cos(angle) * radius, y, Math.sin(angle) * radius];
    });
  });
  return positions;
}

function GraphCanvas({ snapshot, nodes, selectedId, onSelect }: { snapshot: PauliverseSnapshot; nodes: PauliverseNode[]; selectedId: string; onSelect: (id: string) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const positions = useMemo(() => buildPositions(snapshot.nodes), [snapshot.nodes]);

  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    renderer.setClearColor(0x050505, 1);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x050505, 18, 42);
    const camera = new THREE.PerspectiveCamera(48, canvas.clientWidth / canvas.clientHeight, 0.1, 100);
    camera.position.set(0, 12, 19);
    camera.lookAt(0, 0, 0);

    scene.add(new THREE.AmbientLight(0xffffff, 1.1));
    const core = new THREE.PointLight(0xc8aa32, 24, 28);
    core.position.set(0, 7, 0);
    scene.add(core);

    const visibleIds = new Set(nodes.map((node) => node.id));
    const clickable: THREE.Mesh[] = [];

    for (const edge of snapshot.edges) {
      if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) continue;
      const source = positions[edge.source];
      const target = positions[edge.target];
      if (!source || !target) continue;
      const geometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...source), new THREE.Vector3(...target)]);
      const material = new THREE.LineBasicMaterial({ color: edge.active ? 0xc8aa32 : 0x3f3f46, transparent: true, opacity: edge.active ? 0.72 : 0.25 });
      scene.add(new THREE.Line(geometry, material));
    }

    for (const node of nodes) {
      const position = positions[node.id] || [0, 0, 0];
      const radius = node.type === 'REPOSITORY' ? 0.54 : node.type === 'AGENT' ? 0.46 : 0.38;
      const color = STATUS_COLOR[node.status || ''] || 0xd6d3d1;
      const material = new THREE.MeshStandardMaterial({ color, roughness: 0.35, emissive: node.id === selectedId ? color : 0x000000, emissiveIntensity: node.id === selectedId ? 0.55 : 0.08 });
      const sphere = new THREE.Mesh(new THREE.SphereGeometry(radius * (node.id === selectedId ? 1.35 : 1), 24, 24), material);
      sphere.position.set(...position);
      sphere.userData.nodeId = node.id;
      scene.add(sphere);
      clickable.push(sphere);
    }

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const onPointer = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObjects(clickable, false)[0];
      if (hit?.object?.userData?.nodeId) onSelect(hit.object.userData.nodeId);
    };
    canvas.addEventListener('pointerdown', onPointer);

    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    const pivot = new THREE.Group();
    while (scene.children.length > 0) {
      const object = scene.children[0];
      if (object === pivot) break;
      if (object === core || object instanceof THREE.Light) break;
      scene.remove(object);
      pivot.add(object);
    }
    scene.add(pivot);

    const onDown = (event: MouseEvent) => { dragging = true; lastX = event.clientX; lastY = event.clientY; };
    const onMove = (event: MouseEvent) => {
      if (!dragging) return;
      pivot.rotation.y += (event.clientX - lastX) * 0.005;
      pivot.rotation.x = Math.max(-0.5, Math.min(0.5, pivot.rotation.x + (event.clientY - lastY) * 0.003));
      lastX = event.clientX; lastY = event.clientY;
    };
    const onUp = () => { dragging = false; };
    canvas.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);

    let frame = 0;
    const animate = () => {
      pivot.rotation.y += dragging ? 0 : 0.0007;
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    animate();

    const onResize = () => {
      camera.aspect = canvas.clientWidth / canvas.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(frame);
      canvas.removeEventListener('pointerdown', onPointer);
      canvas.removeEventListener('mousedown', onDown);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('resize', onResize);
      scene.traverse((object) => {
        const mesh = object as THREE.Mesh;
        mesh.geometry?.dispose?.();
        const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(material)) material.forEach((item) => item.dispose());
        else material?.dispose?.();
      });
      renderer.dispose();
    };
  }, [snapshot, nodes, selectedId, onSelect, positions]);

  return <canvas ref={canvasRef} className="block h-[620px] w-full cursor-grab active:cursor-grabbing" />;
}

export default function CommandWorld({ snapshot }: { snapshot: PauliverseSnapshot }) {
  const [selectedId, setSelectedId] = useState(snapshot.nodes[0]?.id || '');
  const [query, setQuery] = useState('');
  const selected = snapshot.nodes.find((node) => node.id === selectedId) || snapshot.nodes[0];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return snapshot.nodes;
    return snapshot.nodes.filter((node) => [node.name, node.repo, node.status, node.authority, node.summary, node.type].filter(Boolean).some((value) => String(value).toLowerCase().includes(needle)));
  }, [query, snapshot.nodes]);

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
      <div className="overflow-hidden border border-white/10 bg-black">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
          <div><div className="text-[10px] uppercase tracking-[0.28em] text-amber-100/60">Pauliverse Command World</div><div className="mt-1 text-xs text-stone-500">{snapshot.nodes.length} real nodes · {snapshot.edges.length} provenance-backed relationships</div></div>
          <label className="flex items-center gap-2 border border-white/10 bg-[#0e0e0e] px-3 py-2 text-xs text-stone-400"><Search className="h-3.5 w-3.5" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find repo, agent, opportunity…" className="w-52 bg-transparent outline-none placeholder:text-stone-700" /></label>
        </div>
        <GraphCanvas snapshot={snapshot} nodes={filtered} selectedId={selectedId} onSelect={setSelectedId} />
        <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-white/10 px-4 py-3 text-[10px] uppercase tracking-wider text-stone-500">{Object.entries(STATUS_CSS).map(([status, color]) => <span key={status} className="flex items-center gap-2"><i className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />{status.replaceAll('_', ' ')}</span>)}</div>
      </div>
      <aside className="border border-white/10 bg-[#0e0e0e] p-5">
        {!selected ? <div className="text-sm text-stone-500">Select a node to inspect its authority, evidence and current action.</div> : <div className="space-y-5">
          <div><div className="text-[10px] uppercase tracking-[0.28em] text-stone-600">{selected.type}</div><h2 className="mt-2 text-xl font-semibold text-white">{selected.name}</h2><div className="mt-2 flex flex-wrap gap-2 text-[10px] uppercase tracking-wider"><span className="border border-white/10 px-2 py-1 text-stone-300">{selected.status || 'UNKNOWN'}</span><span className="border border-white/10 px-2 py-1 text-stone-500">{selected.disposition || 'UNCLASSIFIED'}</span></div></div>
          <dl className="space-y-4 text-xs"><div><dt className="uppercase tracking-wider text-stone-600">Authority</dt><dd className="mt-1 leading-5 text-stone-300">{selected.authority || 'Not recorded'}</dd></div><div><dt className="uppercase tracking-wider text-stone-600">Health</dt><dd className="mt-1 leading-5 text-stone-300">{selected.health || 'Not recorded'}</dd></div><div><dt className="uppercase tracking-wider text-stone-600">Summary</dt><dd className="mt-1 leading-5 text-stone-300">{selected.summary || 'Not recorded'}</dd></div></dl>
          {!!selected.active_missions?.length && <div><div className="text-[10px] uppercase tracking-wider text-stone-600">Active missions</div><div className="mt-2 space-y-1 text-xs text-amber-100/70">{selected.active_missions.map((mission) => <div key={mission}>{mission}</div>)}</div></div>}
          {!!selected.financial_signals?.length && <div><div className="text-[10px] uppercase tracking-wider text-stone-600">Financial signals</div><div className="mt-2 flex flex-wrap gap-2">{selected.financial_signals.map((signal) => <span key={signal} className="border border-emerald-400/20 px-2 py-1 text-[10px] text-emerald-200">{signal}</span>)}</div></div>}
          {!!selected.owner_approvals_required?.length && <div className="border border-amber-300/20 bg-amber-300/5 p-3"><div className="text-[10px] uppercase tracking-wider text-amber-200">Owner gates</div><ul className="mt-2 space-y-1 text-xs leading-5 text-amber-100/70">{selected.owner_approvals_required.map((gate) => <li key={gate}>• {gate}</li>)}</ul></div>}
          {!!selected.evidence_refs?.length && <div><div className="text-[10px] uppercase tracking-wider text-stone-600">Evidence</div><ul className="mt-2 space-y-2 text-xs leading-5 text-stone-400">{selected.evidence_refs.map((ref) => <li key={ref}>{ref}</li>)}</ul></div>}
          {(selected.deployment_url || selected.repo) && <div className="flex flex-wrap gap-2 border-t border-white/10 pt-4">{selected.deployment_url && <a href={selected.deployment_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 border border-white/10 px-3 py-2 text-xs text-stone-300 hover:text-white">Open deployment <ExternalLink className="h-3 w-3" /></a>}{selected.repo && <a href={`https://github.com/${selected.repo}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 border border-white/10 px-3 py-2 text-xs text-stone-300 hover:text-white">Open repo <ExternalLink className="h-3 w-3" /></a>}</div>}
          <div className="border-t border-white/10 pt-4 text-[10px] leading-5 text-stone-600">Source: {selected.provenance?.source_ref || snapshot.source}<br />Observed: {selected.provenance?.observed_at || snapshot.generated_at}<br />Confidence: {selected.provenance?.confidence ?? 'n/a'}</div>
        </div>}
      </aside>
    </div>
  );
}
