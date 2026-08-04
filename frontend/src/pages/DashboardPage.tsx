import { useState, useEffect, useCallback, useMemo } from 'react';
import { useAppStore } from '@/store/appStore';
import { api } from '@/lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import { KpiStatCards } from './dashboard/KpiStatCards';
import { LatencyChart } from './dashboard/LatencyChart';
import { ModelTable } from './dashboard/ModelTable';
import { ProviderTabs } from './dashboard/ProviderTabs';
import { ModelChipGrid } from './dashboard/ModelChipGrid';
import type { LatencyRecordOut } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Play } from 'lucide-react';

export default function DashboardPage() {
  const { providers, setProviders, selectedModels, toggleModel } = useAppStore();
  const [activeTab, setActiveTab] = useState<string>('');
  const [probing, setProbing] = useState(false);
  const [latencyCache, setLatencyCache] = useState<LatencyRecordOut[]>([]);

  // Load providers on mount
  useEffect(() => {
    api.listProviders().then(setProviders).catch(() => {});
  }, [setProviders]);

  // Set first provider as active tab
  useEffect(() => {
    if (!activeTab && providers.length > 0) {
      setActiveTab(providers[0].name);
    }
  }, [providers, activeTab]);

  const currentProvider = providers.find(p => p.name === activeTab);
  const currentModels = currentProvider?.models || [];
  const activeModels = selectedModels[activeTab] || [];

  // WebSocket for real-time probe results
  const handleWsMessage = useCallback((data: any) => {
    if (data.type === 'probe_result') {
      setLatencyCache(prev => {
        const next = [...prev, {
          provider: data.provider,
          model: data.model,
          latency_ms: data.latency_ms,
          timestamp: data.timestamp,
          success: data.success,
        }];
        return next.slice(-600);
      });
    }
  }, []);

  const { send } = useWebSocket('ws://localhost:19876/ws/dashboard', handleWsMessage);

  // Subscribe to selected models via WebSocket
  useEffect(() => {
    send({ type: 'subscribe', providers: selectedModels });
  }, [selectedModels, send]);

  // Trigger probe for all selected models
  async function handleProbe() {
    setProbing(true);
    const allModels: string[] = [];
    for (const [, models] of Object.entries(selectedModels)) {
      for (const model of models) {
        allModels.push(model);
      }
    }
    if (allModels.length === 0) {
      setProbing(false);
      return;
    }
    try {
      const results = await api.probe([activeTab], allModels);
      for (const r of results) {
        if (r.latency_ms !== null) {
          const lat = r.latency_ms;
          setLatencyCache(prev => {
            const next = [...prev, {
              provider: r.provider,
              model: r.model,
              latency_ms: lat,
              timestamp: r.timestamp,
              success: r.success,
            }];
            return next.slice(-600);
          });
        }
      }
    } catch { /* ignore probe errors */ }
    finally { setProbing(false); }
  }

  // Auto-probe every 30 seconds
  useEffect(() => {
    if (activeModels.length === 0) return;
    const interval = setInterval(handleProbe, 30000);
    return () => clearInterval(interval);
  }, [activeModels]);

  // Compute KPIs
  const kpis = useMemo(() => {
    const relevantRecords = latencyCache.filter(r => r.provider === activeTab);
    const latencies = relevantRecords.map(r => r.latency_ms).sort((a, b) => a - b);
    const onlineCount = relevantRecords.filter(r => r.success).length;
    return {
      monitored: activeModels.length,
      p50: latencies.length > 0 ? latencies[Math.floor(latencies.length * 0.5)] : 0,
      p90: latencies.length > 0 ? latencies[Math.floor(latencies.length * 0.9)] : 0,
      onlineRate: relevantRecords.length > 0 ? (onlineCount / relevantRecords.length * 100) : 100,
    };
  }, [latencyCache, activeTab, activeModels.length]);

  // Model table data
  const modelRows = useMemo(() => {
    return activeModels.map(mname => {
      const modelRecords = latencyCache.filter(r => r.provider === activeTab && r.model === mname);
      const last = modelRecords[modelRecords.length - 1];
      const latencies = modelRecords.map(r => r.latency_ms).sort((a, b) => a - b);
      return {
        model: mname,
        lastLatency: last?.latency_ms ?? null,
        p50: latencies.length > 0 ? latencies[Math.floor(latencies.length * 0.5)] : null,
        p90: latencies.length > 0 ? latencies[Math.floor(latencies.length * 0.9)] : null,
        online: last?.success ?? null,
        records: modelRecords.length,
      };
    });
  }, [latencyCache, activeTab, activeModels]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'auto', padding: 12 }}>
      {/* Provider tabs + model selection */}
      <ProviderTabs
        providers={providers}
        activeTab={activeTab}
        onSelect={setActiveTab}
      />
      {currentModels.length > 0 && (
        <ModelChipGrid
          models={currentModels}
          selected={activeModels}
          onToggle={(model) => toggleModel(activeTab, model)}
        />
      )}

      {/* Probe button */}
      <div style={{ margin: '8px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Button size="sm" onClick={handleProbe} disabled={probing || activeModels.length === 0}>
          <Play size={12} /> {probing ? 'Probing...' : 'Probe All'}
        </Button>
        <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          {activeModels.length} model(s) selected
        </span>
      </div>

      {/* KPI Stats */}
      <KpiStatCards kpis={kpis} />

      {/* Latency Chart */}
      <div style={{ marginTop: 12 }}>
        <LatencyChart records={latencyCache.filter(r => r.provider === activeTab)} />
      </div>

      {/* Model Table */}
      <div style={{ marginTop: 16 }}>
        <ModelTable rows={modelRows} />
      </div>
    </div>
  );
}
