'use client';

import { useEffect, useState } from 'react';
import { Package, DollarSign, TrendingUp, AlertTriangle } from 'lucide-react';

export default function ProductsPage() {
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/products/')
      .then(r => r.json())
      .then(d => setProducts(d.items || []))
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-2">Products</h1>
      <p className="text-gray-400 mb-6">All products across platforms</p>

      {loading ? (
        <div className="text-gray-400">Loading products...</div>
      ) : products.length === 0 ? (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-12 text-center">
          <Package className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-300">No products yet</h3>
          <p className="text-gray-500 mt-2">
            Products will appear here when agents create them from trends.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {products.map((p) => (
            <div key={p.id} className="bg-gray-900 rounded-xl border border-gray-800 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs px-2 py-0.5 bg-gray-800 rounded text-gray-400 capitalize">{p.platform}</span>
                <span className="text-xs px-2 py-0.5 bg-gray-800 rounded text-gray-400">{p.product_type}</span>
              </div>
              <h3 className="font-medium text-sm line-clamp-2">{p.title}</h3>
              <div className="flex items-center justify-between mt-3">
                <span className="text-lg font-bold">${p.price}</span>
                <span className={`text-xs px-2 py-0.5 rounded capitalize ${
                  p.status === 'published' ? 'bg-green-500/10 text-green-400' :
                  p.status === 'pending_approval' ? 'bg-yellow-500/10 text-yellow-400' :
                  'bg-gray-800 text-gray-400'
                }`}>{p.status}</span>
              </div>
              <div className="text-xs text-gray-500 mt-2">{p.niche}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
