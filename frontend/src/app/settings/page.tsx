'use client';

import { useState } from 'react';
import { Settings as SettingsIcon, Database, Cpu, Globe, Key } from 'lucide-react';

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-2">Settings</h1>
      <p className="text-gray-400 mb-8">System configuration</p>

      <div className="space-y-6 max-w-2xl">
        {/* Database */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Database className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold">Database</h2>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Postgres</span>
              <span className="text-green-400">Connected</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Redis</span>
              <span className="text-green-400">Connected</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Tables</span>
              <span className="text-white">9</span>
            </div>
          </div>
        </div>

        {/* LLM */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Cpu className="w-5 h-5 text-purple-400" />
            <h2 className="text-lg font-semibold">LLM Configuration</h2>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Primary Model</span>
              <span className="text-white">Groq (Free)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Strategist</span>
              <span className="text-white">Llama-3.3-70b</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Workhorse</span>
              <span className="text-white">Llama-3.1-8b</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Image Gen</span>
              <span className="text-white">DALL-E 3 (OpenAI)</span>
            </div>
          </div>
        </div>

        {/* API */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Globe className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-semibold">API Configuration</h2>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Backend URL</span>
              <span className="text-white font-mono text-xs">http://31.220.58.212:8090</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Frontend URL</span>
              <span className="text-white font-mono text-xs">https://paulis-place.vercel.app</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Vercel Project</span>
              <span className="text-white">paulis-place</span>
            </div>
          </div>
        </div>

        {/* Cost Guards */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Key className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold">Cost Guards</h2>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Daily AI Budget</span>
              <span className="text-white">$5.00</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Cost per Idea</span>
              <span className="text-white">$0.10 max</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Cost per Product</span>
              <span className="text-white">$0.25 max</span>
            </div>
          </div>
        </div>

        <button
          onClick={handleSave}
          className="px-6 py-3 bg-brand-500 hover:bg-brand-600 rounded-lg text-sm font-medium transition-colors"
        >
          {saved ? 'Saved!' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
