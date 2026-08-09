'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  ListChecks,
  Users,
  Map,
  PlugZap,
  Factory,
  Brain,
  Eye,
  Settings,
  ShieldCheck,
  Radio,
} from 'lucide-react';
import clsx from 'clsx';

const primary = [
  { href: '/', label: 'Today', icon: Home },
  { href: '/missions', label: 'Missions', icon: ListChecks },
  { href: '/agents', label: 'Agents', icon: Users },
  { href: '/lounge', label: "Pauli's World", icon: Map },
  { href: '/integrations', label: 'Connections', icon: PlugZap },
];

const factory = [
  { href: '/products', label: 'Factory', icon: Factory },
  { href: '/research', label: 'Research', icon: Brain },
  { href: '/observation', label: 'Observation', icon: Eye },
  { href: '/queue', label: 'Approvals', icon: ShieldCheck },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <>
      <aside className="hidden md:flex fixed inset-y-0 left-0 z-40 w-[248px] flex-col border-r border-white/[0.07] bg-[#0a0a09]/95 backdrop-blur-xl">
        <Link href="/" className="px-5 pt-6 pb-5 border-b border-white/[0.06] group">
          <div className="flex items-center gap-3">
            <div className="relative h-10 w-10 rounded-full border border-white/15 bg-stone-100 text-stone-950 grid place-items-center font-black tracking-tight shadow-[0_0_30px_rgba(255,255,255,.08)]">
              P
              <span className="absolute -right-0.5 -bottom-0.5 h-3 w-3 rounded-full bg-[#79c493] border-2 border-[#0a0a09]" />
            </div>
            <div>
              <h1 className="font-semibold tracking-tight text-[15px] group-hover:text-white">Pauli's Place</h1>
              <p className="text-[10px] uppercase tracking-[0.18em] text-stone-600 mt-0.5">The house is working</p>
            </div>
          </div>
        </Link>

        <nav className="flex-1 overflow-y-auto px-3 py-4 scrollbar-thin">
          <div className="eyebrow px-3 mb-2">Control</div>
          <div className="space-y-1">
            {primary.map((item) => <NavItem key={item.href} item={item} pathname={pathname} />)}
          </div>

          <div className="eyebrow px-3 mt-7 mb-2">Under the hood</div>
          <div className="space-y-1">
            {factory.map((item) => <NavItem key={item.href} item={item} pathname={pathname} />)}
          </div>
        </nav>

        <div className="p-4 border-t border-white/[0.06]">
          <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-3.5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-xs text-stone-400">
                <Radio className="w-3.5 h-3.5" /> House status
              </div>
              <span className="status-dot status-live" />
            </div>
            <div className="text-xs text-stone-600 mt-2 leading-relaxed">Voice, missions, agents and tools share one control plane.</div>
          </div>
        </div>
      </aside>

      <nav className="md:hidden fixed bottom-0 inset-x-0 z-50 border-t border-white/10 bg-[#090908]/95 backdrop-blur-2xl px-2 pb-[max(.45rem,env(safe-area-inset-bottom))] pt-1.5">
        <div className="grid grid-cols-5 gap-1">
          {primary.map((item) => {
            const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <Link key={item.href} href={item.href}
                className={clsx('min-w-0 rounded-xl py-2 flex flex-col items-center gap-1 text-[9px] font-medium transition', active ? 'text-stone-100 bg-white/[0.07]' : 'text-stone-600')}>
                <item.icon className="w-[18px] h-[18px]" />
                <span className="truncate max-w-full">{item.label === "Pauli's World" ? 'World' : item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}

function NavItem({ item, pathname }: { item: { href: string; label: string; icon: any }; pathname: string }) {
  const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
  return (
    <Link href={item.href}
      className={clsx(
        'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] transition',
        active ? 'bg-stone-100 text-stone-950 font-semibold shadow-sm' : 'text-stone-500 hover:text-stone-100 hover:bg-white/[0.045]'
      )}>
      <item.icon className={clsx('w-4 h-4 shrink-0', active ? 'text-stone-950' : 'text-stone-600 group-hover:text-stone-300')} />
      <span>{item.label}</span>
    </Link>
  );
}
