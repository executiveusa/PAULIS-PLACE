'use client';

import { useEffect, useState } from 'react';
import { api, ApprovalQueue, Product } from '@/lib/api';
import { Check, X, Upload, Image as ImageIcon } from 'lucide-react';
import clsx from 'clsx';

export default function ApprovalQueuePage() {
  const [queue, setQueue] = useState<ApprovalQueue | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [imageCache, setImageCache] = useState<Record<number, string>>({});

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    try {
      const data = await api.approvals.getQueue();
      setQueue(data);

      // Load images for pending items
      for (const product of data.pending.slice(0, 5)) {
        if (!imageCache[product.id]) {
          try {
            const img = await api.products.getImage(product.id);
            setImageCache(prev => ({ ...prev, [product.id]: img.base64 }));
          } catch (e) {}
        }
      }
    } catch (e) {
      console.error('Failed to load queue');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const processAction = async (action: 'approve' | 'reject' | 'publish') => {
    if (selected.size === 0) return;
    setProcessing(true);
    try {
      await api.approvals.process(Array.from(selected), action);
      setSelected(new Set());
      await loadQueue();
    } catch (e) {
      console.error('Action failed');
    } finally {
      setProcessing(false);
    }
  };

  if (loading) return <div className="p-8 text-gray-400">Loading...</div>;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Approval Queue</h1>
          <p className="text-gray-400 mt-1">{queue?.pending.length || 0} items waiting for review</p>
        </div>

        {selected.size > 0 && (
          <div className="flex gap-3">
            <button
              onClick={() => processAction('reject')}
              disabled={processing}
              className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 rounded-lg text-sm transition-colors"
            >
              <X className="w-4 h-4" />
              Reject ({selected.size})
            </button>
            <button
              onClick={() => processAction('approve')}
              disabled={processing}
              className="flex items-center gap-2 px-4 py-2 bg-green-500/10 text-green-400 hover:bg-green-500/20 rounded-lg text-sm transition-colors"
            >
              <Check className="w-4 h-4" />
              Approve ({selected.size})
            </button>
          </div>
        )}
      </div>

      {/* Pending Items */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {queue?.pending.map((product) => (
          <div
            key={product.id}
            className={clsx(
              'bg-gray-900 rounded-xl border overflow-hidden cursor-pointer transition-all',
              selected.has(product.id) ? 'border-brand-500 ring-2 ring-brand-500/30' : 'border-gray-800 hover:border-gray-600'
            )}
            onClick={() => toggleSelect(product.id)}
          >
            <div className="aspect-square bg-gray-800 relative">
              {imageCache[product.id] ? (
                <img
                  src={`data:image/png;base64,${imageCache[product.id]}`}
                  alt={product.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-600">
                  <ImageIcon className="w-12 h-12" />
                </div>
              )}
              {selected.has(product.id) && (
                <div className="absolute top-2 right-2 w-6 h-6 bg-brand-500 rounded-full flex items-center justify-center">
                  <Check className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
            <div className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs px-2 py-0.5 bg-gray-800 rounded text-gray-400 capitalize">
                  {product.platform}
                </span>
                <span className="text-xs px-2 py-0.5 bg-gray-800 rounded text-gray-400">
                  {product.product_type}
                </span>
              </div>
              <h3 className="font-medium text-sm line-clamp-2">{product.title}</h3>
              <div className="flex items-center justify-between mt-3">
                <span className="text-lg font-bold">${product.price}</span>
                <span className="text-xs text-gray-500">{product.niche}</span>
              </div>
              {product.research_data?.trend_keyword && (
                <div className="mt-2 text-xs text-gray-500">
                  Trend: {product.research_data.trend_keyword}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Ready to Publish */}
      {queue && queue.ready_to_publish.length > 0 && (
        <div className="mt-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold">Ready to Publish</h2>
            <button
              onClick={() => {
                setSelected(new Set(queue.ready_to_publish.map(p => p.id)));
                processAction('publish');
              }}
              disabled={processing}
              className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm font-medium transition-colors"
            >
              <Upload className="w-4 h-4" />
              Publish All ({queue.ready_to_publish.length})
            </button>
          </div>

          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left text-sm font-medium text-gray-400 px-4 py-3">Title</th>
                  <th className="text-left text-sm font-medium text-gray-400 px-4 py-3">Platform</th>
                  <th className="text-left text-sm font-medium text-gray-400 px-4 py-3">Price</th>
                  <th className="text-left text-sm font-medium text-gray-400 px-4 py-3">Niche</th>
                  <th className="text-right text-sm font-medium text-gray-400 px-4 py-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {queue.ready_to_publish.map((product) => (
                  <tr key={product.id} className="border-b border-gray-800/50 hover:bg-gray-800/50">
                    <td className="px-4 py-3 text-sm">{product.title.slice(0, 50)}...</td>
                    <td className="px-4 py-3 text-sm capitalize text-gray-400">{product.platform}</td>
                    <td className="px-4 py-3 text-sm font-medium">${product.price}</td>
                    <td className="px-4 py-3 text-sm text-gray-400">{product.niche}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => {
                          setSelected(new Set([product.id]));
                          processAction('publish');
                        }}
                        className="text-sm text-brand-500 hover:text-brand-400"
                      >
                        Publish
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
