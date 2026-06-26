'use client';

import { useEffect, useState } from 'react';
import { api, Trend } from '@/lib/api';
import { TrendingUp, TrendingDown, Minus, Zap, Eye, Target } from 'lucide-react';
import clsx from 'clsx';

export default function TrendsPage() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // This would need a trends endpoint - for now mock
    setLoading(false);
  }, []);

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Trend Monitor</h1>
          <p className="text-gray-400 mt-1">Google Trends analysis for your niches</p>
        </div>
        <button
          onClick={async () => {
            await api.triggers.scanTrends();
            await api.triggers.scoreTrends();
          }}
          className="px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm font-medium transition-colors"
        >
          Scan Now
        </button>
      </div>

      {loading ? (
        <div className="text-gray-400">Loading trends...</div>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-8 text-center">
          <Target className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-300">No trends scanned yet</h3>
          <p className="text-gray-500 mt-2 max-w-md mx-auto">
            Click "Scan Now" to analyze Google Trends for your configured niches.
            The system will identify opportunities and score them automatically.
          </p>
        </div>
      )}

      {/* Example of what trend cards would look like */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
        {[
          { keyword: 'anime sticker pack', niche: 'anime', score: 78, change: 45, isBreakout: false },
          { keyword: 'dark aesthetic wallpaper', niche: 'aesthetic', score: 72, change: 120, isBreakout: true },
          { keyword: 'kawaii planner stickers', niche: 'kawaii', score: 65, change: -5, isBreakout: false },
        ].map((trend, i) => (
          <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  {trend.isBreakout && (
                    <span className="flex items-center gap-1 text-xs px-2 py-0.5 bg-yellow-500/10 text-yellow-400 rounded">
                      <Zap className="w-3 h-3" />
                      Breakout
                    </span>
                  )}
                </div>
                <h3 className="font-medium mt-2">{trend.keyword}</h3>
                <span className="text-xs text-gray-500 capitalize">{trend.niche}</span>
              </div>
              <div className={clsx(
                'flex items-center gap-1 text-sm',
                trend.change > 0 ? 'text-green-400' : trend.change < 0 ? 'text-red-400' : 'text-gray-400'
              )}>
                {trend.change > 0 ? <TrendingUp className="w-4 h-4" /> :
                  trend.change < 0 ? <TrendingDown className="w-4 h-4" /> : <Minus className="w-4 h-4" />}
                {trend.change > 0 ? '+' : ''}{trend.change}%
              </div>
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Opportunity Score</span>
                <span className="font-bold">{trend.score}/100</span>
              </div>
              <div className="mt-2 h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 rounded-full"
                  style={{ width: `${trend.score}%` }}
                />
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-800 flex gap-2">
              <button className="flex-1 text-sm px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                <Eye className="w-3 h-3 inline mr-1" />
                View
              </button>
              <button className="flex-1 text-sm px-3 py-1.5 bg-brand-500 hover:bg-brand-600 rounded-lg transition-colors">
                Create Product
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
