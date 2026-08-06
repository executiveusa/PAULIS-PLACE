import dynamic from 'next/dynamic';

const LoungeClient = dynamic(() => import('@/components/lounge/LoungeClient'), { ssr: false });

export const metadata = {
  title: "Paulie's Place · 3D Lounge",
  description: 'Yappyverse 3D observable world — voice Jarvis, avatars, real-time agent scenes',
};

export default function LoungePage() {
  return <LoungeClient />;
}