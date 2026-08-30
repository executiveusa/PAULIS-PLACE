'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  Banknote,
  Brain,
  Building2,
  Factory,
  MessageCircle,
  PlugZap,
  Radio,
  Settings,
  ShieldCheck,
  Sparkles,
  Users,
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { href: '/', label: 'Talk', icon: MessageCircle },
  { href: '/', label: 'Today', icon: Activity },
  { href: '/observation', label: 'Agents', icon: Users },
  { href: '/products', label: 'Businesses', icon: Building2 },
  { href: '/research', label: 'Factory', icon: Factory },
  { href: '/queue', label: 'Approvals', icon: ShieldCheck },
  { href: '/trends', label: 'Signal', icon: Brain },
  { href: '/lounge', label: 'World', icon: Radio },
  { href: '/integrations', label: 'Integrations', icon: PlugZap },
  { href: '/settings', label: 'Settings', icon: Settings },
];

const primary = [
  { href: '/', label: 'Pauli', icon: MessageCircle },
  { href: '/products', label: 'Businesses', icon: Building2 },
  { href: '/queue', label: 'Approvals', icon: ShieldCheck },
  { href: '/observation', label: 'Work', icon: Activity },
  { href: '/lounge', label: "Pauli's World", icon: Radio },
];

export function Sidebar() {
  const pathname = usePathname();

  // The owner Home owns its own calm four-surface navigation. Technical chrome
  // only appears after the owner deliberately drills into an operator route.
  if (pathname === '/') return null;

  return (
    <>
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-white/10 bg-[#0b0b0b] lg:flex">
        <div className="border-b border-white/10 p-6">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-amber-200/25 bg-amber-100/[0.03]">
              <Sparkles className="h-4 w-4 text-amber-100/80" />
            </div>
            <div>
              <h1 className="font-semibold tracking-tight">Pauli's Place</h1>
              <p className="mt-0.5 text-[10px] uppercase tracking-[0.18em] text-stone-600">Mission Control</p>
            </div>
          </Link>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item, index) => {
            const isActive = pathname === item.href && (item.href !== '/' || index === 0);
            return (
              <Link
                key={`${item.href}-${item.label}`}
                href={item.href}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 text-sm transition-colors active:scale-[0.985]',
                  isActive
                    ? 'bg-white/[0.05] text-stone-100'
                    : 'text-stone-500 hover:bg-white/[0.03] hover:text-stone-200'
                )}
              >
                <item.icon className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-white/10 p-4">
          <div className="border border-white/10 bg-black/20 p-4">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-stone-600">
              <Banknote className="h-3.5 w-3.5" />
              Treasury policy
            </div>
            <p className="mt-3 text-xs leading-5 text-stone-400">Routine reversible work can run autonomously. Consequential actions remain scoped and approval-gated.</p>
          </div>
        </div>
      </aside>

      <nav className="fixed bottom-0 inset-x-0 z-50 border-t border-white/10 bg-[#090908]/95 px-2 pb-[max(.45rem,env(safe-area-inset-bottom))] pt-1.5 backdrop-blur-2xl md:hidden">
        <div className="grid grid-cols-5 gap-1">
          {primary.map((item) => {
            const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  'flex min-w-0 flex-col items-center gap-1 rounded-xl py-2 text-[9px] font-medium transition active:scale-[0.96]',
                  active ? 'bg-white/[0.07] text-stone-100' : 'text-stone-600'
                )}
              >
                <item.icon className="h-[18px] w-[18px]" />
                <span className="max-w-full truncate">{item.label === "Pauli's World" ? 'World' : item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
