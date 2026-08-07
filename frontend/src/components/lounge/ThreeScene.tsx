'use client';

import { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { LoungeAvatarState } from '@/lib/loungeApi';
import { AVATAR_ROSTER } from '@/lib/demo';

interface Props {
  avatars?: LoungeAvatarState[];
  speakingAvatarId?: string | null;
  sceneCue?: string | null;
}

const IDLE_COLOR_BY_ROLE: Record<string, number> = {
  av_paulie: 0xE6DCFF, av_zia: 0x5B9BD5, av_marco: 0x4DC99A,
  av_dex:    0xA080E0, av_sasha: 0xD4A017, av_wren: 0xE05A5A,
  av_niko:   0x6B5F8A, av_mira:  0xC8AA32,
};

// If the backend is down we still fill the room with the roster — the lounge is
// never empty. When a real LoungeState arrives it simply overrides positions.
function resolvedAvatars(avatars?: LoungeAvatarState[]): LoungeAvatarState[] {
  if (avatars && avatars.length > 0) return avatars;
  return AVATAR_ROSTER.map((a) => ({
    id: a.id, name: a.name, position: a.position, model: a.model, state: a.state,
  }));
}

/**
 * Always-rendering 3D lounge. Per high-end game/ambient principles:
 *  - every player character has alive idle motion (breathing + micro-sway),
 *  - the speaking avatar lifts, warms its rim light and glows,
 *  - the room has subtle atmosphere: floating dust, a neon sign pulse,
 *    a low mono-light chemistry so it feels like a jazz room, not a widget.
 */
export default function ThreeScene({ avatars, speakingAvatarId, sceneCue }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    renderer.setClearColor(0x0A0714, 1);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x0A0714, 12, 38);

    const camera = new THREE.PerspectiveCamera(50, canvas.clientWidth / canvas.clientHeight, 0.1, 100);
    camera.position.set(0, 3.6, 11);
    camera.lookAt(0, 0.9, 0);

    // Ambient + jazz lights
    const ambient = new THREE.AmbientLight(0x352244, 0.5);
    scene.add(ambient);

    const spot = new THREE.SpotLight(0xFFD07A, 5.5, 30, Math.PI / 5.5, 0.5, 1.2);
    spot.position.set(0, 7, 4); spot.target.position.set(0, 0.5, 0);
    spot.castShadow = true;
    scene.add(spot, spot.target);

    const rim = new THREE.PointLight(0xC8AA32, 1.8, 14);
    rim.position.set(-5, 2.5, -2); scene.add(rim);

    const neon = new THREE.PointLight(0xFF6432, 1.6, 20);
    neon.position.set(5, 2.5, -3); scene.add(neon);

    // Floor
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(40, 40),
      new THREE.MeshStandardMaterial({ color: 0x140F1E, roughness: 0.6, metalness: 0.12 })
    );
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true;
    scene.add(floor);

    // Rug
    const rug = new THREE.Mesh(
      new THREE.CircleGeometry(3.4, 48),
      new THREE.MeshStandardMaterial({ color: 0x2A1F3D, roughness: 0.85 })
    );
    rug.rotation.x = -Math.PI / 2; rug.position.y = 0.012; rug.position.z = 0.8;
    scene.add(rug);

    // Bar counter
    const bar = new THREE.Mesh(
      new THREE.BoxGeometry(6.4, 1.1, 1.0),
      new THREE.MeshStandardMaterial({ color: 0x1A1230, roughness: 0.45 })
    );
    bar.position.set(0, 0.55, -3.4); scene.add(bar);
    const barTop = new THREE.Mesh(
      new THREE.BoxGeometry(6.6, 0.07, 1.2),
      new THREE.MeshStandardMaterial({ color: 0xC8AA32, roughness: 0.3, metalness: 0.75 })
    );
    barTop.position.set(0, 1.14, -3.4); scene.add(barTop);

    // Stools
    const stool = new THREE.Mesh(
      new THREE.CylinderGeometry(0.22, 0.3, 0.65, 20),
      new THREE.MeshStandardMaterial({ color: 0x2A1F3D, roughness: 0.6 })
    );
    stool.position.set(-1.8, 0.33, -2.6); scene.add(stool);
    const stool2 = stool.clone(); stool2.position.set(1.8, 0.33, -2.6); scene.add(stool2);

    // Stage platform
    const stage = new THREE.Mesh(
      new THREE.CylinderGeometry(2.1, 2.4, 0.16, 40),
      new THREE.MeshStandardMaterial({ color: 0x140F1E, roughness: 0.5 })
    );
    stage.position.set(0, 0.08, 2); scene.add(stage);

    // Mic
    const mic = new THREE.Mesh(
      new THREE.CylinderGeometry(0.05, 0.08, 0.7, 16),
      new THREE.MeshStandardMaterial({ color: 0xC8AA32, metalness: 0.9, roughness: 0.2 })
    );
    mic.position.set(0, 1.05, 2); scene.add(mic);

    // Neon sign mesh (emissive — reads as signage without font plumbing)
    const signFrame = new THREE.Mesh(
      new THREE.PlaneGeometry(2.6, 0.8),
      new THREE.MeshBasicMaterial({ color: 0x301818, side: THREE.DoubleSide })
    );
    signFrame.position.set(0, 2.6, -3.9); scene.add(signFrame);
    const signGlow = new THREE.Mesh(
      new THREE.PlaneGeometry(2.4, 0.65),
      new THREE.MeshStandardMaterial({ color: 0xFF6432, emissive: 0xFF3A2A, emissiveIntensity: 1.4, side: THREE.DoubleSide, transparent: true, opacity: 1 })
    );
    signGlow.position.set(0, 2.6, -3.88); scene.add(signGlow);

    // Floating dust motes for atmosphere
    const dust: THREE.Mesh[] = [];
    const dustGeom = new THREE.SphereGeometry(0.02, 6, 6);
    const dustMat = new THREE.MeshBasicMaterial({ color: 0xC8AA32, transparent: true, opacity: 0.5 });
    for (let i = 0; i < 60; i++) {
      const d = new THREE.Mesh(dustGeom, dustMat);
      d.position.set((Math.random() - 0.5) * 16, Math.random() * 5 + 0.5, (Math.random() - 0.5) * 14);
      d.userData = { phase: Math.random() * Math.PI * 2, speed: 0.2 + Math.random() * 0.5 };
      scene.add(d);
      dust.push(d);
    }

    const ROSTER = resolvedAvatars(avatars || []);

    // Avatars — always present, always breathing
    const avatarMeshes: Record<string, THREE.Group> = {};
    const heads = new Map<string, THREE.Mesh>();
    const bodies = new Map<string, THREE.Mesh>();

    ROSTER.forEach((av) => {
      const g = new THREE.Group();
      g.position.set(av.position[0], 0, av.position[2]);
      g.rotation.y = Math.atan2(0 - av.position[0], 0 - av.position[2]) * 0.2;

      const color = IDLE_COLOR_BY_ROLE[av.id] ?? 0xE6DCFF;
      const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.3, 28, 28),
        new THREE.MeshStandardMaterial({ color, roughness: 0.4, metalness: 0.2, emissive: 0x000000 })
      );
      head.position.y = 1.62; head.castShadow = true;

      const body = new THREE.Mesh(
        new THREE.CapsuleGeometry(0.32, 1.0, 14, 28),
        new THREE.MeshStandardMaterial({ color: 0x1A1230, roughness: 0.55 })
      );
      body.position.y = 0.9; body.castShadow = true;

      g.add(head, body);
      scene.add(g);
      avatarMeshes[av.id] = g;
      heads.set(av.id, head);
      bodies.set(av.id, body);
    });

    let raf = 0;
    let t = 0;

    const animate = () => {
      t += 0.008;

      // Idle breathing for every avatar + gentle body sway; speakers rise + glow.
      for (const id of Object.keys(avatarMeshes)) {
        const g = avatarMeshes[id];
        const head = heads.get(id)!;
        const body = bodies.get(id)!;
        const speaking = speakingAvatarId != null && id === speakingAvatarId;

        const breathe = Math.sin(t * 2.4 + (id.charCodeAt(0) % 7));
        g.position.y = breathe * 0.02 + (speaking ? Math.sin(t * 5) * 0.05 : 0);
        g.position.x += Math.sin(t * 1.3 + id.length * 0.9) * 0.0008;
        head.rotation.z = Math.sin(t * 1.1 + 0.4 * id.length) * 0.06;
        body.rotation.z = Math.sin(t * 0.9 + 0.7 * id.length) * 0.02;

        const mat = head.material as THREE.MeshStandardMaterial;
        if (speaking) {
          mat.emissive.setHex(0xFF6432);
          mat.emissiveIntensity = 0.55 + Math.sin(t * 8) * 0.25;
        } else {
          mat.emissive.setHex(0x221533);
          mat.emissiveIntensity = 0.12;
        }
      }

      // Dust drift
      for (const d of dust) {
        d.position.y += Math.sin(t * (d.userData.speed * 2) + d.userData.phase) * 0.004;
        d.position.x += Math.sin(t * 0.4 + d.userData.phase) * 0.0016;
      }

      // Stage mic + neon flicker
      mic.position.y = 1.05 + Math.sin(t * 3) * 0.008;
      neon.intensity = 1.6 + Math.sin(t * 7) * 0.35;
      signGlow.material.opacity = 0.85 + Math.sin(t * 2.2) * 0.15;

      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };
    animate();
    setReady(true);

    const onResize = () => {
      if (!canvas) return;
      camera.aspect = canvas.clientWidth / canvas.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      scene.traverse((o) => {
        if ((o as THREE.Mesh).geometry) (o as THREE.Mesh).geometry.dispose();
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [avatars, speakingAvatarId, sceneCue]);

  return (
    <div className="relative w-full h-[560px] rounded-2xl overflow-hidden border border-[#2A1F3D] bg-[#0A0714]">
      <canvas ref={canvasRef} className="w-full h-full block" />
      {!ready && <div className="absolute inset-0 grid place-items-center text-[#C8AA32]">drawing the lounge…</div>}
    </div>
  );
}