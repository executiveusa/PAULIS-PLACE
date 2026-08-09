import dynamic from 'next/dynamic';

const LoungeClient = dynamic(() => import('@/components/lounge/LoungeClient'), { ssr: false });

export const metadata = {
  title: "Pauli's World · Live 3D Operations",
  description: "A live, voice-first 3D view of Pauli's Place agents, missions and meetings.",
};

export default function LoungePage() {
  return <LoungeClient />;
}
