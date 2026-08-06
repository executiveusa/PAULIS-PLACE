'use client';

import { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { lounge as loungeApi, LoungeAvatarState } from '@/lib/loungeApi';

interface Props {
  avatars: LoungeAvatarState[];
  speakingAvatarId: string | null;
  sceneCue?: string;
}

/**
 * A minimal but production-shape Three.js lounge scene.
 * Per emilkowalski/skills emil-design-eng, I'm not animating
 * unnecessarily — only idle "breathing" on the actively-speaking avatar.
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

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x0A0714, 10, 35);

    const camera = new THREE.PerspectiveCamera(50, canvas.clientWidth / canvas.clientHeight, 0.1, 100);
    camera.position.set(0, 3.5, 10);
    camera.lookAt(0, 0.8, 0);

    // Lights — warm, low, jazz-room
    const ambient = new THREE.AmbientLight(0x352244, 0.55);
    scene.add(ambient);
    const spot = new THREE.SpotLight(0xFFD07A, 4.0, 25, Math.PI / 6, 0.5, 1);
    spot.position.set(0, 6, 3); spot.target.position.set(0, 0, 0);
    scene.add(spot, spot.target);
    const rim = new THREE.PointLight(0xC8AA32, 1.8, 14);
    rim.position.set(-4, 2, -2); scene.add(rim);
    const neon = new THREE.PointLight(0xFF6432, 1.4, 18);
    neon.position.set(4, 2, -3); scene.add(neon);

    // Floor — dark wood w/ subtle spec
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(40, 40),
      new THREE.MeshStandardMaterial({ color: 0x140F1E, roughness: 0.65, metalness: 0.1 })
    );
    floor.rotation.x = -Math.PI / 2; scene.add(floor);

    // Bar counter
    const bar = new THREE.Mesh(
      new THREE.BoxGeometry(6, 1.1, 1.0),
      new THREE.MeshStandardMaterial({ color: 0x1A1230, roughness: 0.45 })
    );
    bar.position.set(0, 0.55, -3); scene.add(bar);
    const barTop = new THREE.Mesh(
      new THREE.BoxGeometry(6.2, 0.08, 1.2),
      new THREE.MeshStandardMaterial({ color: 0xC8AA32, roughness: 0.35, metalness: 0.7 })
    );
    barTop.position.set(0, 1.13, -3); scene.add(barTop);

    // Stage
    const stage = new THREE.Mesh(
      new THREE.CylinderGeometry(2, 2, 0.18, 32),
      new THREE.MeshStandardMaterial({ color: 0x140F1E, roughness: 0.5 })
    );
    stage.position.set(0, 0.09, 2); scene.add(stage);

    // Microphone
    const mic = new THREE.Mesh(
      new THREE.CylinderGeometry(0.04, 0.07, 0.6, 16),
      new THREE.MeshStandardMaterial({ color: 0xC8AA32, metalness: 0.9, roughness: 0.2 })
    );
    mic.position.set(0, 1.0, 2); scene.add(mic);

    // Avatars — placeholder capsules (no model files yet, see icm/context/CHARACTER_REGISTRY)
    const avatarMeshes: Record<string, THREE.Group> = {};
    const SSH_COLOR_COMMUNICATING = 0xFF6432;
    const IDLE_COLOR_BY_ROLE: Record<string, number> = {
      av_paulie: 0xE6DCFF, av_zia: 0x5B9BD5, av_marco: 0x4DC99A,
      av_dex:    0xA080E0, av_sasha: 0xD4A017, av_wren: 0xE05A5A,
      av_niko:   0x6B5F8A, av_mira:  0xC8AA32,
    };

    avatars.forEach((av) => {
      const g = new THREE.Group();
      const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.28, 24, 24),
        new THREE.MeshStandardMaterial({ color: IDLE_COLOR_BY_ROLE[av.id] ?? 0xE6DCFF,
                                         roughness: 0.45, metalness: 0.15 })
      );
      head.position.y = 1.55;
      const body = new THREE.Mesh(
        new THREE.CapsuleGeometry(0.3, 1.0, 12, 24),
        new THREE.MeshStandardMaterial({ color: 0x1A1230, roughness: 0.55 })
      );
      body.position.y = 0.95;
      g.add(head, body);
      g.position.set(av.position[0], 0, av.position[2]);
      g.userData.avId = av.id;
      scene.add(g);
      avatarMeshes[av.id] = g;
    });

    // Sign behind bar — "NO SOLICITORS"
    const signGeom = new THREE.PlaneGeometry(2.2, 0.6);
    const signMat = new THREE.MeshBasicMaterial({ color: 0xFF3A3A, side: THREE.DoubleSide });
    const sign = new THREE.Mesh(signGeom, signMat);
    sign.position.set(0, 2.4, -3.5);
    // We don't render text via SDF (avoids an extra font asset); the geometry is the signage.

    let raf = 0;
    let t = 0;
    const animate = () => {
      t += 0.012;
      // Idle breathing only on the speaking avatar; emil-design-eng: no wasted motion
      for (const id of Object.keys(avatarMeshes)) {
        const m = avatarMeshes[id];
        const speaking = id === speakingAvatarId;
        if (speaking) {
          m.position.y = Math.sin(t * 4.0) * 0.06;
          (m.children[0] as THREE.Mesh).material &&
            (((m.children[0] as THREE.Mesh).material as THREE.MeshStandardMaterial).emissive
              .setHex(SSH_COLOR_COMMUNICATING));
        } else {
          m.position.y = 0;
          ((m.children[0] as THREE.Mesh).material as THREE.MeshStandardMaterial).emissive.setHex(0x000000);
        }
      }
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
  }, [avatars, speakingAvatarId, sceneCue]);

  return (
    <div className="relative w-full h-[560px] rounded-2xl overflow-hidden border border-[#2A1F3D] bg-[#0A0714]">
      <canvas ref={canvasRef} className="w-full h-full block" />
      {!ready && <div className="absolute inset-0 grid place-items-center text-[#C8AA32]">drawing the lounge…</div>}
    </div>
  );
}