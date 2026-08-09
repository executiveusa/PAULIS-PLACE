'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import type { PauliAgent } from '@/lib/api';

export type WorldMode = 'live' | 'director';

interface Props {
  agents: PauliAgent[];
  selectedAgentId?: string | null;
  onSelectAgent?: (agent: PauliAgent) => void;
  mode?: WorldMode;
}

const POSITIONS: [number, number, number][] = [
  [0, 0, 1.6], [-2.0, 0, .9], [2.0, 0, .9], [-3.0, 0, -.7], [3.0, 0, -.7], [-1.45, 0, -1.9], [1.45, 0, -1.9],
];

export default function ThreeScene({ agents, selectedAgentId, onSelectAgent, mode = 'live' }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [ready, setReady] = useState(false);
  const latestRef = useRef({ agents, selectedAgentId, onSelectAgent });
  latestRef.current = { agents, selectedAgentId, onSelectAgent };

  const key = useMemo(() => `${mode}:${agents.map(a => `${a.id}:${a.status}`).join('|')}`, [agents, mode]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    renderer.setClearColor(0x080807, 1);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = .82;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x080807);
    scene.fog = new THREE.Fog(0x080807, 8, 22);

    const camera = new THREE.PerspectiveCamera(mode === 'director' ? 38 : 44, canvas.clientWidth / canvas.clientHeight, .1, 80);
    camera.position.set(mode === 'director' ? 7.2 : 0, mode === 'director' ? 4.4 : 3.1, mode === 'director' ? 8.0 : 8.8);
    camera.lookAt(0, 1.0, -.5);

    scene.add(new THREE.AmbientLight(0xb8b0a0, .22));
    const keyLight = new THREE.DirectionalLight(0xf2e5cf, 2.7);
    keyLight.position.set(3, 8, 5); keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048); scene.add(keyLight);
    const warm = new THREE.PointLight(0xd3b885, 30, 9); warm.position.set(-4.2, 3.2, -1.4); scene.add(warm);
    const cool = new THREE.PointLight(0x81909b, 15, 7); cool.position.set(4.3, 2.8, -2.8); scene.add(cool);

    const floor = new THREE.Mesh(new THREE.PlaneGeometry(22, 18), new THREE.MeshStandardMaterial({ color: 0x171714, roughness: .34, metalness: .11 }));
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

    const backWall = new THREE.Mesh(new THREE.BoxGeometry(15, 5.8, .35), new THREE.MeshStandardMaterial({ color: 0x171714, roughness: .92 }));
    backWall.position.set(0, 2.9, -5); backWall.receiveShadow = true; scene.add(backWall);

    const brickMatA = new THREE.MeshStandardMaterial({ color: 0x292823, roughness: .98 });
    const brickMatB = new THREE.MeshStandardMaterial({ color: 0x22211e, roughness: .98 });
    for (let row = 0; row < 11; row += 1) {
      for (let col = 0; col < 9; col += 1) {
        const brick = new THREE.Mesh(new THREE.BoxGeometry(1.58, .34, .065), (row + col) % 3 === 0 ? brickMatA : brickMatB);
        brick.position.set(-6.65 + col * 1.68 + (row % 2) * .82, .34 + row * .46, -4.79);
        scene.add(brick);
      }
    }

    // Bar: restrained metal/wood, no purple SaaS styling.
    const bar = new THREE.Mesh(new THREE.BoxGeometry(5.8, 1.05, 1.05), new THREE.MeshStandardMaterial({ color: 0x28251f, roughness: .48 }));
    bar.position.set(-3.5, .54, -2.75); bar.castShadow = true; scene.add(bar);
    const barTop = new THREE.Mesh(new THREE.BoxGeometry(6.1, .1, 1.3), new THREE.MeshStandardMaterial({ color: 0x8b8271, roughness: .29, metalness: .22 }));
    barTop.position.set(-3.5, 1.1, -2.75); barTop.castShadow = true; scene.add(barTop);

    const table = new THREE.Mesh(new THREE.CylinderGeometry(1.55, 1.55, .15, 48), new THREE.MeshStandardMaterial({ color: 0x2b2924, roughness: .4 }));
    table.position.set(1.55, .76, -1.45); table.castShadow = true; scene.add(table);
    const pedestal = new THREE.Mesh(new THREE.CylinderGeometry(.18, .48, .68, 20), new THREE.MeshStandardMaterial({ color: 0x151513, metalness: .5, roughness: .3 }));
    pedestal.position.set(1.55, .36, -1.45); scene.add(pedestal);

    // Doorway focal point, derived from the canonical Pauli exterior direction.
    const doorway = new THREE.Mesh(new THREE.BoxGeometry(2.0, 3.15, .2), new THREE.MeshStandardMaterial({ color: 0x070706, roughness: .8 }));
    doorway.position.set(4.75, 1.58, -4.68); scene.add(doorway);
    const sign = new THREE.Mesh(new THREE.BoxGeometry(2.5, .5, .24), new THREE.MeshStandardMaterial({ color: 0xd8d3c7, roughness: .8 }));
    sign.position.set(4.75, 3.42, -4.66); scene.add(sign);

    // Booths.
    [-1.8, 1.4].forEach((x) => {
      const seat = new THREE.Mesh(new THREE.BoxGeometry(2.2, .85, .72), new THREE.MeshStandardMaterial({ color: 0x23211e, roughness: .73 }));
      seat.position.set(x, .43, 2.65); seat.castShadow = true; scene.add(seat);
      const top = new THREE.Mesh(new THREE.BoxGeometry(1.65, .12, .8), new THREE.MeshStandardMaterial({ color: 0x39342c, roughness: .52 }));
      top.position.set(x, .68, 2.0); top.castShadow = true; scene.add(top);
    });

    const avatarGroups: Array<{ agent: PauliAgent; group: THREE.Group; head: THREE.Mesh; baseY: number }> = [];
    agents.forEach((agent, index) => {
      const pos = POSITIONS[index % POSITIONS.length];
      const group = new THREE.Group(); group.position.set(pos[0], 0, pos[2]); group.userData.agentId = agent.id;
      const isPauli = agent.agent_key === 'pauli';
      const head = new THREE.Mesh(new THREE.SphereGeometry(isPauli ? .45 : .36, 28, 22), new THREE.MeshStandardMaterial({ color: isPauli ? 0xbeb9ad : 0x85837c, roughness: .84 }));
      head.position.y = 1.72; head.castShadow = true; group.add(head);
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(isPauli ? .44 : .36, isPauli ? .86 : .78, 8, 18), new THREE.MeshStandardMaterial({ color: isPauli ? 0x1f1f1c : 0x373630, roughness: .7 }));
      body.position.y = .98; body.castShadow = true; group.add(body);
      if (isPauli) {
        const earMat = new THREE.MeshStandardMaterial({ color: 0xa9a59b, roughness: .9 });
        const leftEar = new THREE.Mesh(new THREE.ConeGeometry(.14, .38, 14), earMat); leftEar.position.set(-.31, 1.93, -.02); leftEar.rotation.z = -.58; group.add(leftEar);
        const rightEar = leftEar.clone(); rightEar.position.x = .31; rightEar.rotation.z = .58; group.add(rightEar);
        const shirt = new THREE.Mesh(new THREE.BoxGeometry(.08, .68, .025), new THREE.MeshStandardMaterial({ color: 0xd2cdc0 })); shirt.position.set(0,1.1,-.42); group.add(shirt);
      }
      [-1,1].forEach((dir) => {
        const arm = new THREE.Mesh(new THREE.CapsuleGeometry(.105,.66,5,12), new THREE.MeshStandardMaterial({ color: 0x272620 })); arm.position.set(dir*.48,.98,0); arm.rotation.z=dir*.08; arm.castShadow=true; group.add(arm);
        const leg = new THREE.Mesh(new THREE.CapsuleGeometry(.12,.62,5,12), new THREE.MeshStandardMaterial({ color: 0x171715 })); leg.position.set(dir*.2,.27,0); leg.castShadow=true; group.add(leg);
      });
      scene.add(group); avatarGroups.push({ agent, group, head, baseY: 0 });
    });

    // Atmospheric dust only; no fake operational events.
    const dust: THREE.Mesh[] = [];
    const dustGeom = new THREE.SphereGeometry(.012, 5, 5);
    const dustMat = new THREE.MeshBasicMaterial({ color: 0xd0c5ae, transparent: true, opacity: .26 });
    for (let i=0;i<45;i+=1) { const d=new THREE.Mesh(dustGeom,dustMat); d.position.set((Math.random()-.5)*13,Math.random()*4.5+.5,(Math.random()-.5)*10); d.userData.phase=Math.random()*6.28; scene.add(d); dust.push(d); }

    const raycaster = new THREE.Raycaster(); const pointer = new THREE.Vector2();
    const click = (ev: PointerEvent) => {
      const rect=canvas.getBoundingClientRect(); pointer.x=((ev.clientX-rect.left)/rect.width)*2-1; pointer.y=-((ev.clientY-rect.top)/rect.height)*2+1;
      raycaster.setFromCamera(pointer,camera); const hit=raycaster.intersectObjects(avatarGroups.map(a=>a.group),true)[0];
      if (!hit) return; let obj:THREE.Object3D|null=hit.object; while(obj && !obj.userData.agentId) obj=obj.parent;
      const agent=latestRef.current.agents.find(a=>a.id===obj?.userData.agentId); if(agent) latestRef.current.onSelectAgent?.(agent);
    };
    canvas.addEventListener('pointerup',click);

    let raf=0; const animate=()=>{ const t=performance.now()/1000;
      avatarGroups.forEach(({agent,group,head})=>{ const active=['working','meeting','recovering'].includes(agent.status); group.position.y=Math.sin(t*1.25+group.position.x)*.018; group.rotation.y=active?Math.sin(t*.5+group.position.z)*.055:0; const mat=head.material as THREE.MeshStandardMaterial; const selected=latestRef.current.selectedAgentId===agent.id; mat.emissive.setHex(selected?0x4b4437:active?0x211e18:0); mat.emissiveIntensity=selected?.7:active?.25:0; });
      dust.forEach((d)=>{ d.position.y += Math.sin(t*.4+d.userData.phase)*.0009; }); renderer.render(scene,camera); raf=requestAnimationFrame(animate); };
    animate(); setReady(true);

    const resize=()=>{camera.aspect=canvas.clientWidth/canvas.clientHeight;camera.updateProjectionMatrix();renderer.setSize(canvas.clientWidth,canvas.clientHeight,false);}; window.addEventListener('resize',resize);
    return ()=>{ cancelAnimationFrame(raf); canvas.removeEventListener('pointerup',click); window.removeEventListener('resize',resize); renderer.dispose(); scene.traverse((o:any)=>{o.geometry?.dispose?.(); if(o.material){const mats=Array.isArray(o.material)?o.material:[o.material];mats.forEach((m:any)=>m.dispose?.());}}); };
  }, [key]);

  return <div className="relative w-full h-full min-h-[420px] overflow-hidden bg-[#080807]">
    <canvas ref={canvasRef} className="w-full h-full block" />
    {!ready && <div className="absolute inset-0 grid place-items-center text-xs uppercase tracking-[.2em] text-stone-600">Opening Pauli's Place…</div>}
    <div className="absolute left-4 top-4 rounded-full border border-white/10 bg-black/60 px-3 py-1.5 text-[10px] uppercase tracking-[.17em] text-stone-400 backdrop-blur">Seattle · after hours · {mode}</div>
  </div>;
}
