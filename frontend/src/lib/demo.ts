// Demo/data engine — mirrors the exact backend API contract so the UI is always
// alive and animated, and transparently upgrades to a real backend when one is
// reachable. This is the UIGen philosophy: the UI is driven by a firm API
// contract; the data source (real API vs embedded mirror) is interchangeable.

import type { DashboardStats, RevenueData, NicheData, Product } from './api';

export const AVATAR_ROSTER = [
  { id: 'av_paulie', name: 'Paulie', position: [0.0, 0, 2.2] as [number, number, number], model: 'GLM-5.2 Strategist', state: 'idle' },
  { id: 'av_zia', name: 'Zia', position: [-1.6, 0, 1.4] as [number, number, number], model: 'DeepSeek Workhorse', state: 'idle' },
  { id: 'av_marco', name: 'Marco', position: [1.6, 0, 1.4] as [number, number, number], model: 'Ornith-1 Critic', state: 'idle' },
  { id: 'av_dex', name: 'Dex', position: [-2.4, 0, 0.4] as [number, number, number], model: 'Alpha-Owl Evaluator', state: 'idle' },
  { id: 'av_sasha', name: 'Sasha', position: [2.4, 0, 0.4] as [number, number, number], model: 'GLM-4 Grunt', state: 'idle' },
  { id: 'av_wren', name: 'Wren', position: [-1.0, 0, -0.4] as [number, number, number], model: 'DeepSeek Workhorse', state: 'idle' },
  { id: 'av_niko', name: 'Niko', position: [1.0, 0, -0.4] as [number, number, number], model: 'Commentator', state: 'idle' },
  { id: 'av_mira', name: 'Mira', position: [0.0, 0, -1.2] as [number, number, number], model: 'Human-in-the-loop', state: 'idle' },
];

interface TaskRow { stage: string; task: string; tier: string; text: string }

const TASK_POOL: TaskRow[] = [
  { stage: 'SCAN', task: 'scan_all_trends', tier: 'workhorse', text: 'scanning trend feeds for breakout signals' },
  { stage: 'SCORE', task: 'score_hot_trends', tier: 'workhorse', text: 'scoring opportunity signals' },
  { stage: 'DESIGN', task: 'design_product', tier: 'workhorse', text: 'drafting product concepts from trending niches' },
  { stage: 'PUBLISH', task: 'publish_product', tier: 'grunt', text: 'pushing the new drop to Printify' },
  { stage: 'RECONCILE', task: 'reconcile_ledger', tier: 'grunt', text: 'reconciling the payment ledger' },
  { stage: 'COUNCIL', task: 'council_debate', tier: 'critic', text: 'debating a proposal in the chamber' },
  { stage: 'JUDGE', task: 'judge_output', tier: 'critic', text: 'judging envelope quality against L1' },
  { stage: 'VOICE', task: 'voice_intent', tier: 'grunt', text: 'interpreting a lounge voice command' },
];

const MODELS = ['GLM-5.2', 'DeepSeek', 'Ornith-1', 'Alpha-Owl', 'GLM-4'];

let counter = 0;

function nowTs() { return Math.floor(Date.now() / 1000); }
function iso() { return new Date().toISOString(); }
function rnd(n: number, d = 0) { return +(Math.random() * n).toFixed(d); }
function pick<T>(arr: T[]): T { return arr[Math.floor(Math.random() * arr.length)]; }

function taskRow() { return pick(TASK_POOL); }

function makeEnvelope() {
  counter += 1;
  const row = taskRow();
  const body = { response_text: row.text };
  return {
    event_id: `demo_${Date.now()}_${counter}`,
    route: `R-${rnd(5)}:${row.stage}`,
    stage: 'completed',
    ts: iso(),
    services_touched: ['demo-engine'],
    blast_radius_usd: rnd(0.02, 4),
    worker_profile: row.tier,
    worker_model: pick(MODELS),
    judge_verdict: 'pass',
    judge_model: pick(MODELS),
    envelope_version: '1.0-demo',
    next_action: null,
    body,
  };
}

export const demo = {
  counter: () => counter,

  health(): Promise<any> {
    const spent = 0.42 + counter * 0.0007;
    const cap = 25;
    return Promise.resolve({
      status: spent < cap ? 'ok' : 'cap_reached',
      spent_usd: Number(spent.toFixed(4)),
      cap_usd: cap,
      remaining_usd: Number((cap - spent).toFixed(4)),
      routes_known: 52,
      laws: { L1: 'judge_every_output', L2: 'blast_radius<=3', L3: 'cap_usd', L4: 'no_secrets' },
    });
  },

  envelopes(limit = 20): Promise<{ envelopes: any[] }> {
    const out: any[] = [];
    for (let i = 0; i < limit; i++) out.unshift(makeEnvelope());
    return Promise.resolve({ envelopes: out });
  },

  loungeState() {
    const perf = Math.floor(Date.now() / 7000) % 8;
    const avatars = AVATAR_ROSTER.map((a, i) => ({
      ...a,
      state: i === perf ? 'communicating' : 'idle',
    }));
    return Promise.resolve({
      lounge: "Paulie's Place",
      setting: 'Seattle 2056 · jazz lounge · 3D observable world',
      avatars,
      schedule_cue: rnd(2) > 1 ? 'Niko: "two-drink minimum."' : "Mira: tonight's drop is live",
    });
  },

  scenes(limit = 20): Promise<{ scenes: any[] }> {
    const items: any[] = [];
    for (let i = 0; i < limit; i++) items.push(makeEnvelope());
    return Promise.resolve({ scenes: items });
  },

  logs(limit = 50): any[] {
    const out: any[] = [];
    for (let i = 0; i < limit; i++) {
      const row = taskRow();
      out.push({
        timestamp: nowTs() - i * 37 - rnd(20),
        task_type: row.task,
        model: pick(MODELS),
        tier: row.tier,
        cost: rnd(0.02, 5),
        input_tokens: rnd(90000),
        output_tokens: rnd(90000),
      });
    }
    return out.sort((a, b) => b.timestamp - a.timestamp);
  },

  costs() {
    const calls = 40 + counter;
    const byModel: Record<string, number> = {};
    MODELS.forEach((m) => { byModel[m] = rnd(0.2, 4); });
    const total = Object.values(byModel).reduce((a, b) => a + b, 0);
    return Promise.resolve({
      total_cost: Number(total.toFixed(4)),
      call_count: calls,
      avg_cost_per_call: Number((total / calls).toFixed(6)),
      by_model: byModel,
    });
  },

  research(topic: string, depth = 'standard'): Promise<any> {
    const confidence = depth === 'standard' ? 0.82 + rnd(0.1) : 0.68 + rnd(0.1);
    return Promise.resolve({
      topic,
      confidence: Math.min(0.99, confidence),
      searches_used: depth === 'standard' ? 7 + rnd(5) : 3 + rnd(2),
      gaps_filled: 4 + rnd(3),
      cost: depth === 'standard' ? 0.05 * (1 + rnd(0.2)) : 0.02 * (1 + rnd(0.2)),
      money_angles: [
        { angle: `Limited gold-foil ${topic} poster`, pattern: 'Nostalgia merch sells at 400% markup on print-on-demand', expected_monthly_revenue: 840 + rnd(400), cost_to_make: 8.4, price_to_sell: 34, units_to_break_even: 12 },
        { angle: `${topic} themed brass barware set`, pattern: 'Lounge-adjacent niche buyers ignore price once themed', expected_monthly_revenue: 600 + rnd(300), cost_to_make: 11, price_to_sell: 48, units_to_break_even: 9 },
        { angle: `Desk-envy ${topic} accessory line`, pattern: 'Low-craft barware sells during late-night scrolls', expected_monthly_revenue: 330 + rnd(200), cost_to_make: 4.2, price_to_sell: 29, units_to_break_even: 6 },
      ],
      next_actions: ['Publish the gold-foil edition to Printify immediately', 'A/B the brass card set across Etsy + eBay', 'Watch the niche for 72h before scaling'],
    });
  },

  ideas(method: string, params: Record<string, any> = {}): Promise<any> {
    const niches: Record<string, [string, string]> = {
      mashup: ['candle-making', 'jazz-lounge'],
      etsy_autocomplete: [params.keyword || 'anime sticker', 'budget desk decor'],
      review_mine: ['competitor dropship candle', 'lead streets'],
      bundle: ['smartwatch strap', 'snack tin'],
      pinterest: ['tiny living', 'vinyl desk aesthetic'],
    };
    const [a, b] = niches[method] || niches.mashup;
    const count = params.count || 10;
    const ideas = [];
    for (let i = 0; i < count; i++) {
      ideas.push({
        niche_a: a, niche_b: b, angle: `${a} meets ${b} — #${i + 1}`,
        pattern: 'Search clusters overlap; intersect them into one listing',
        expected_monthly_revenue: 50 + rnd(200),
        fastest_replication: 'Grab top-3 competitor listings, remix headline + specs',
        why_it_works: 'Both niches have proven paid conversion; the intersection is orphaned.',
      });
    }
    return Promise.resolve({ result: { count, ideas }, cost: Number((count * 0.004).toFixed(4)), method });
  },

  wikiStats() {
    const byCloud: Record<string, number> = {};
    ['print-on-demand', 'lounge', 'decor', 'noir', 'money-angle'].forEach((c) => { byCloud[c] = 14 + rnd(40); });
    const total = Object.values(byCloud).reduce((a, b) => a + b, 0);
    return Promise.resolve({ total_entries: total, proven_patterns: total * 0.42, avg_confidence: 0.79, by_category: byCloud });
  },

  wikiSearch(query: string): Promise<any> {
    const results = [
      { relevance: 0.97, entry: { title: `${query} — gold-foil print pattern`, summary: 'Proven by 3 campaigns; margins 4.2x cost.', category: 'print-on-demand', tags: ['decor', 'gold-foil', 'lounge'] } },
      { relevance: 0.91, entry: { title: `${query} — bar-adjacent trinket set`, summary: 'Fast break-even; strong impulse AOV.', category: 'decor', tags: ['bar', 'trinket', 'set'] } },
      { relevance: 0.84, entry: { title: `${query} — limited-colorway strategy`, summary: 'Scarcity lifts conversion 18% in A/B.', category: 'money-angle', tags: ['scarcity', 'colorway'] } },
    ];
    return Promise.resolve({ query, results });
  },

  councilDelibs() {
    return [
      { id: 1, topic: 'Raise daily cap to $25?', status: 'decided', problem_statement: 'Should the factory allow more spend during the drop?', ruling: 'Approved. Cap stays conservative.', total_cost: 0.0421, turns: 3, created_at: iso() },
      { id: 2, topic: 'Which platform first?', status: 'deliberating', problem_statement: 'Printify vs Etsy for the fresh drop', ruling: null, total_cost: 0.0121, turns: 2, created_at: iso() },
      { id: 3, topic: 'Nightly self-improve', status: 'decided', problem_statement: 'Enable auto PR proposals at 03:00 UTC', ruling: 'Approved. Draft only, no merge.', total_cost: 0.0878, turns: 3, created_at: iso() },
    ];
  },

  dashboardStats(): Promise<DashboardStats> {
    const published = 128 + rnd(30);
    const total_sales = 240 + rnd(80);
    return Promise.resolve({
      products: { total: published + 14, published, pending_approval: 9 + rnd(5), drafts: 12 + rnd(4) },
      revenue: {
        total: total_sales * 12.4,
        last_7_days: 380 + rnd(120),
        total_sales,
        by_platform: { printify: { revenue: 2100 + rnd(300), count: 120 + rnd(20) }, etsy: { revenue: 900 + rnd(200), count: 60 + rnd(10) }, fivrr: { revenue: 400 + rnd(100), count: 20 + rnd(5) } },
      },
      trends: { hot: 14 + rnd(5), breakout: 3 + rnd(2) },
      tasks: { running: 2 + rnd(3), failed: rnd(2) },
    });
  },

  revenueChart(days = 30): Promise<RevenueData[]> {
    const out: RevenueData[] = [];
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(Date.now() - i * 86400000);
      out.push({
        date: d.toISOString().slice(0, 10),
        products_created: rnd(6),
        revenue: rnd(120) + 20,
      });
    }
    return Promise.resolve(out);
  },

  niches(): Promise<NicheData[]> {
    return Promise.resolve(['art-deco', 'jazz-lounge', 'noir', 'space-cowboy', 'cyberpunk-diner', 'indigo-print'].map((n, i) => ({
      id: i + 1, niche: n, avg_price: 22 + i * 3, updated_at: iso(),
    })));
  },

  products(limit = 18): Promise<{ total: number; items: Product[] }> {
    const titles = ['Vinyl Blueprint Print', 'Brass Bar Stool Sketch', 'City Rooftop Tumbler', 'Neon Sign Candle', 'Retro Telephone Stand', 'Jazz-Room Poster', 'Warm Rim Lamp'];
    const items: Product[] = [];
    for (let i = 0; i < limit; i++) {
      const status = pick(['published', 'pending_approval', 'draft', 'failed']);
      items.push({
        id: i + 6001, external_id: `d-${Date.now()}-${i}`, platform: pick(['printify', 'etsy', 'fivrr']),
        product_type: pick(['home_decor', 'apparel', 'accessory']), title: pick(titles) + ` #${rnd(9)}`,
        description: 'Designed and judged by the factory', tags: ['Paulie', 'Seattle', '2056'], niche: pick(['jazz-lounge', 'noir-mode', 'art-deco']),
        price: rnd(48) + 12, status, views: rnd(4000), sales: status === 'published' ? rnd(40) : 0,
        revenue: status === 'published' ? rnd(500) : 0, created_at: iso(),
      });
    }
    return Promise.resolve({ total: items.length, items });
  },

  approvalQueue() {
    return { pending: { total: 6, items: demo.productsSync(6) }, ready_to_publish: { total: 3, items: demo.productsSync(3) } };
  },

  productsSync(limit = 10) {
    return demo.products(limit);
  },

  tasks() {
    return [
      { id: 1, task_type: 'scan_all_trends', status: 'running', ai_cost: 0.02, created_at: iso() },
      { id: 2, task_type: 'score_hot_trends', status: 'idle', ai_cost: 0.01, created_at: iso() },
      { id: 3, task_type: 'create_products_from_trends', status: 'completed', ai_cost: 0.02, created_at: iso() },
    ];
  },

  taskSummary() {
    return {
      scan_all_trends: { pending: 1, running: 0, completed: 42, failed: 1 },
      score_hot_trends: { pending: 0, running: 1, completed: 40, failed: 0 },
      create_products_from_trends: { pending: 2, running: 0, completed: 36, failed: 2 },
    };
  },

  activeModelRotation(tick: number) { return MODELS[tick % MODELS.length]; },
};