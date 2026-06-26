'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  TrendingUp,
  Package,
  ClipboardCheck,
  Settings,
  Zap,
  DollarSign,
  Brain,
  Eye
} from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/trends', label: 'Trends', icon: TrendingUp },
  { href: '/products', label: 'Products', icon: Package },
  { href: '/queue', label: 'Approval Queue', icon: ClipboardCheck },
  { href: '/research', label: 'Research Lab', icon: Brain },
  { href: '/observation', label: 'Observation', icon: Eye },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-brand-500 rounded-lg flex items-center justify-center">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg">DigiFactory</h1>
            <p className="text-xs text-gray-400">Autonomous Products</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                isActive
                  ? 'bg-brand-500/10 text-brand-500'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              )}
            >
              <item.icon className="w-5 h-5" />
              <span className="text-sm font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-800">
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex items-center gap-2 text-sm text-gray-300">
            <DollarSign className="w-4 h-4 text-green-400" />
            <span>Today's AI Cost:</span>
          </div>
          <div className="mt-1 text-2xl font-bold text-white">
            $<CostDisplay />
          </div>
          <div className="mt-1 text-xs text-gray-500">Limit: $10.00/day</div>
        </div>
      </div>
    </aside>
  );
}

function CostDisplay() {
  // This would fetch from API
  return '0.00';
}
