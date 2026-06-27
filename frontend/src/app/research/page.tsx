'use client';

import { useState, useEffect } from 'react';
import {
  Search,
  Lightbulb,
  Zap,
  Brain,
  DollarSign,
  ArrowRight,
  RefreshCw,
  BookOpen,
  TrendingUp,
  Target
} from 'lucide-react';

const API_URL = '';

type Tab = 'research' | 'ideas' | 'wiki' | 'costs';

export default function ResearchLabPage() {
  const [activeTab, setActiveTab] = useState<Tab>('research');
  const [researchTopic, setResearchTopic] = useState('');
  const [researchDepth, setResearchDepth] = useState<'quick' | 'standard'>('standard');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const [ideaMethod, setIdeaMethod] = useState('mashup');
  const [ideaParams, setIdeaParams] = useState<any>({ keyword: '', count: 10, competitor_url: '' });
  const [ideaResult, setIdeaResult] = useState<any>(null);

  const handleResearch = async () => {
    if (!researchTopic) return;
    setLoading(true);
    try {
      const data = await fetch(`${API_URL}/api/research-lab/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: researchTopic, depth: researchDepth })
      }).then(r => r.json());
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleIdeas = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (ideaMethod === 'mashup') params.count = ideaParams.count || 10;
      if (ideaMethod === 'etsy_autocomplete') params.keyword = ideaParams.keyword;
      if (ideaMethod === 'review_mine') params.competitor_url = ideaParams.competitor_url;

      const data = await fetch(`${API_URL}/api/research-lab/ideas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method: ideaMethod, params })
      }).then(r => r.json());
      setIdeaResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-3">
          <Brain className="w-8 h-8 text-purple-400" />
          Research Lab
        </h1>
        <p className="text-gray-400 mt-2">
          Ruthless idea generation and deep research. Find what makes money. Copy it.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-8 bg-gray-900 p-1 rounded-lg w-fit">
        {[
          { id: 'research' as Tab, label: 'AutoResearch', icon: Search },
          { id: 'ideas' as Tab, label: 'Idea Factory', icon: Lightbulb },
          { id: 'wiki' as Tab, label: 'LLM Wiki', icon: BookOpen },
          { id: 'costs' as Tab, label: 'Cost Analytics', icon: DollarSign },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors ${
              activeTab === tab.id
                ? 'bg-gray-800 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Research Tab */}
      {activeTab === 'research' && (
        <div className="space-y-6">
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
            <h2 className="text-lg font-semibold mb-4">AutoResearch (Karpathy-Style)</h2>
            <p className="text-sm text-gray-400 mb-4">
              Iterative deep research that fills knowledge gaps until confident enough to act.
            </p>

            <div className="flex gap-4">
              <input
                type="text"
                value={researchTopic}
                onChange={(e) => setResearchTopic(e.target.value)}
                placeholder="e.g., anime sticker market trends 2024"
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-brand-500"
                onKeyDown={(e) => e.key === 'Enter' && handleResearch()}
              />
              <select
                value={researchDepth}
                onChange={(e) => setResearchDepth(e.target.value as any)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm"
              >
                <option value="quick">Quick ($0.02)</option>
                <option value="standard">Standard ($0.05)</option>
              </select>
              <button
                onClick={handleResearch}
                disabled={loading || !researchTopic}
                className="flex items-center gap-2 px-6 py-3 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Research
              </button>
            </div>
          </div>

          {result && (
            <div className="space-y-6">
              <div className="grid grid-cols-4 gap-4">
                <StatCard icon={Target} label="Confidence" value={`${(result.confidence * 100).toFixed(0)}%`} />
                <StatCard icon={Search} label="Searches" value={result.searches_used} />
                <StatCard icon={Zap} label="Gaps Filled" value={result.gaps_filled} />
                <StatCard icon={DollarSign} label="Cost" value={`$${result.cost?.toFixed(4) || '0.0000'}`} />
              </div>

              <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-green-400" />
                  Money Angles ({result.money_angles?.length || 0})
                </h3>
                <div className="space-y-4">
                  {result.money_angles?.map((angle: any, i: number) => (
                    <div key={i} className="bg-gray-800 rounded-lg p-4">
                      <div className="flex items-start justify-between">
                        <h4 className="font-medium">{angle.angle}</h4>
                        <span className="text-xs px-2 py-1 bg-green-500/10 text-green-400 rounded">
                          ${(angle.expected_monthly_revenue || 0).toFixed(0)}/mo
                        </span>
                      </div>
                      <p className="text-sm text-gray-400 mt-2">{angle.pattern}</p>
                      <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">Cost:</span>
                          <span className="ml-2">${angle.cost_to_make?.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Price:</span>
                          <span className="ml-2">${angle.price_to_sell?.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Break even:</span>
                          <span className="ml-2">{angle.units_to_break_even} units</span>
                        </div>
                      </div>
                      <button className="mt-3 text-sm text-brand-500 hover:text-brand-400 flex items-center gap-1">
                        Create Product <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                <h3 className="text-lg font-semibold mb-4">Next Actions</h3>
                <div className="space-y-2">
                  {result.next_actions?.map((action: string, i: number) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
                      <div className="w-6 h-6 bg-brand-500/20 text-brand-500 rounded-full flex items-center justify-center text-xs font-bold">
                        {i + 1}
                      </div>
                      <span className="text-sm">{action}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Ideas Tab */}
      {activeTab === 'ideas' && (
        <div className="space-y-6">
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
            <h2 className="text-lg font-semibold mb-4">Idea Factory</h2>

            <div className="grid grid-cols-5 gap-3 mb-6">
              {[
                { id: 'mashup', label: 'Mashup Generator', desc: 'Combine unrelated niches' },
                { id: 'etsy_autocomplete', label: 'Etsy Spy', desc: 'Steal buyer intent' },
                { id: 'review_mine', label: 'Review Miner', desc: 'Exploit weaknesses' },
                { id: 'bundle', label: 'Bundle Architect', desc: '3x your AOV' },
                { id: 'pinterest', label: 'Pinterest Pilot', desc: 'Free traffic' },
              ].map(method => (
                <button
                  key={method.id}
                  onClick={() => setIdeaMethod(method.id)}
                  className={`p-4 rounded-lg border text-left transition-colors ${
                    ideaMethod === method.id
                      ? 'border-brand-500 bg-brand-500/10'
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <div className="font-medium text-sm">{method.label}</div>
                  <div className="text-xs text-gray-500 mt-1">{method.desc}</div>
                </button>
              ))}
            </div>

            {ideaMethod === 'mashup' && (
              <div className="flex gap-4">
                <input
                  type="number"
                  value={ideaParams.count}
                  onChange={(e) => setIdeaParams({ ...ideaParams, count: parseInt(e.target.value) || 10 })}
                  placeholder="Number of ideas"
                  className="w-32 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm"
                />
                <button
                  onClick={handleIdeas}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-3 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm font-medium"
                >
                  {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Lightbulb className="w-4 h-4" />}
                  Generate Mashups
                </button>
              </div>
            )}

            {ideaMethod === 'etsy_autocomplete' && (
              <div className="flex gap-4">
                <input
                  type="text"
                  value={ideaParams.keyword}
                  onChange={(e) => setIdeaParams({ ...ideaParams, keyword: e.target.value })}
                  placeholder="e.g., anime sticker"
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm"
                />
                <button
                  onClick={handleIdeas}
                  disabled={loading || !ideaParams.keyword}
                  className="flex items-center gap-2 px-6 py-3 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm font-medium"
                >
                  {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  Spy on Etsy
                </button>
              </div>
            )}

            {ideaMethod === 'review_mine' && (
              <div className="flex gap-4">
                <input
                  type="url"
                  value={ideaParams.competitor_url || ''}
                  onChange={(e) => setIdeaParams({ ...ideaParams, competitor_url: e.target.value })}
                  placeholder="Competitor product URL"
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm"
                />
                <button
                  onClick={handleIdeas}
                  disabled={loading || !ideaParams.competitor_url}
                  className="flex items-center gap-2 px-6 py-3 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm font-medium"
                >
                  {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}
                  Mine Reviews
                </button>
              </div>
            )}
          </div>

          {ideaResult && (
            <div className="space-y-4">
              <div className="text-sm text-gray-400">
                Generated {ideaResult.result?.count || 0} ideas for ${ideaResult.cost?.toFixed(4) || '0.0000'}
              </div>

              {ideaResult.result?.ideas?.map((idea: any, i: number) => (
                <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-medium">{idea.product_angle || idea.angle || idea.suggestion}</h3>
                      {idea.niche_a && (
                        <div className="flex gap-2 mt-2">
                          <span className="text-xs px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded">{idea.niche_a}</span>
                          <span className="text-xs text-gray-500">+</span>
                          <span className="text-xs px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded">{idea.niche_b}</span>
                        </div>
                      )}
                    </div>
                    {idea.expected_monthly_revenue && (
                      <span className="text-sm font-bold text-green-400">
                        ${idea.expected_monthly_revenue.toFixed(0)}/mo
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mt-3">{idea.pattern || idea.why_it_works}</p>
                  {idea.fastest_replication && (
                    <div className="mt-3 p-3 bg-gray-800 rounded-lg">
                      <div className="text-xs text-gray-500 mb-1">FASTEST PATH TO MONEY</div>
                      <div className="text-sm">{idea.fastest_replication}</div>
                    </div>
                  )}
                  <div className="mt-4 flex gap-3">
                    <button className="text-sm px-4 py-2 bg-brand-500 hover:bg-brand-600 rounded-lg">
                      Create Product
                    </button>
                    <button className="text-sm px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg">
                      Save to Wiki
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'wiki' && <WikiTab />}
      {activeTab === 'costs' && <CostsTab />}
    </div>
  );
}

function StatCard({ icon: Icon, label, value }: { icon: any; label: string; value: string | number }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
        <Icon className="w-4 h-4" />
        {label}
      </div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}

function WikiTab() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const API_URL_LOCAL = '';

  useEffect(() => {
    fetch(`${API_URL_LOCAL}/api/research-lab/wiki/stats`).then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  const handleSearch = async () => {
    if (!query) return;
    setLoading(true);
    try {
      const data = await fetch(`${API_URL_LOCAL}/api/research-lab/wiki/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 20 })
      }).then(r => r.json());
      setResults(data.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard icon={BookOpen} label="Total Entries" value={stats.total_entries || 0} />
          <StatCard icon={TrendingUp} label="Proven Patterns" value={stats.proven_patterns || 0} />
          <StatCard icon={Target} label="Avg Confidence" value={`${((stats.avg_confidence || 0) * 100).toFixed(0)}%`} />
          <StatCard icon={Zap} label="Categories" value={Object.keys(stats.by_category || {}).length} />
        </div>
      )}

      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <div className="flex gap-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the wiki..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-sm"
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-3 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm font-medium"
          >
            <Search className="w-4 h-4" />
            Search
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {results.map((r: any, i: number) => (
          <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-medium text-sm">{r.entry.title}</h3>
                <p className="text-xs text-gray-400 mt-1">{r.entry.summary}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 bg-gray-800 rounded text-gray-400">{r.entry.category}</span>
                <span className="text-xs text-gray-500">{(r.relevance * 100).toFixed(0)}%</span>
              </div>
            </div>
            <div className="flex gap-2 mt-2">
              {r.entry.tags?.slice(0, 5).map((tag: string, j: number) => (
                <span key={j} className="text-xs px-2 py-0.5 bg-gray-800 rounded text-gray-500">{tag}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CostsTab() {
  const [costs, setCosts] = useState<any>(null);
  const API_URL_LOCAL = '';

  useEffect(() => {
    fetch(`${API_URL_LOCAL}/api/research-lab/costs`).then(r => r.json()).then(setCosts).catch(() => {});
  }, []);

  if (!costs) return <div className="text-gray-400">Loading costs...</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatCard icon={DollarSign} label="Total Cost" value={`$${costs.total_cost?.toFixed(4) || '0.0000'}`} />
        <StatCard icon={Zap} label="Total Calls" value={costs.call_count || 0} />
        <StatCard icon={Target} label="Avg Cost/Call" value={`$${costs.avg_cost_per_call?.toFixed(5) || '0.00000'}`} />
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h3 className="text-lg font-semibold mb-4">Cost by Model</h3>
        <div className="space-y-3">
          {Object.entries(costs.by_model || {}).map(([model, cost]: [string, any]) => (
            <div key={model} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
              <div>
                <div className="font-medium text-sm">{model}</div>
                <div className="text-xs text-gray-500">
                  {((cost / (costs.total_cost || 1)) * 100).toFixed(1)}% of total
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold">${cost?.toFixed(4) || '0.0000'}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
