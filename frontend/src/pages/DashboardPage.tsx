import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useAppStore } from '@/store/appStore';
import { api } from '@/lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import { KpiStatCards } from './dashboard/KpiStatCards';
import { LatencyChart } from './dashboard/LatencyChart';
import { ModelTable } from './dashboard/ModelTable';
import { ProviderTabs } from './dashboard/ProviderTabs';
import { ModelChipGrid } from './dashboard/ModelChipGrid';
import type { LatencyRecordOut, ProbeResultOut } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Play, AlertCircle } from 'lucide-react';

const AUTO_PROBE_INTERVAL_MS = 30_000;

interface WsProbeMessage {
  type: string;
  provider: string;
  model: string;
  latency_ms: number | null;
  success: boolean;
  timestamp: string;
}

function resultToRecord(r: { provider: string; model: string; latency_ms: number | null; success: boolean; timestamp: string }): LatencyRecordOut {
  return {
    provider: r.provider,
    model: r.model,
    latency_ms: r.latency_ms ?? 0,
    timestamp: r.timestamp,
    success: r.success,
  };
}

export default function DashboardPage() {
  const {
    providers,
    setProviders,
    selectedModels,
    toggleModel,
    appendLatency,
    latencyCache,
  } = useAppStore();
  const [activeTab, setActiveTab] = useState<string>('');
  const [probing, setProbing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load providers on mount
  useEffect(() => {
    api.listProviders()
      .then(data => { setProviders(data); setError(null); })
      .catch(() => setError('Failed to load providers'));
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

  // Stabilise activeTab via ref so the interval always probes the right provider
  const activeTabRef = useRef(activeTab);
  activeTabRef.current = activeTab;

  // Selected models as flat list (ref for interval use)
  const activeModelsRef = useRef(activeModels);
  activeModelsRef.current = activeModels;

  // --- Probe function (useCallback so the interval sees latest deps) ---
  const handleProbe = useCallback(async () => {
    const tab = activeTabRef.current;
    const models = activeModelsRef.current;
    if (models.length === 0) return;

    setProbing(true);
    try {
      const results: ProbeResultOut[] = await api.probe([tab], models);
      const valid = results
        .filter((r): r is ProbeResultOut & { latency_ms: number } => r.latency_ms !== null)
        .map(resultToRecord);
      if (valid.length > 0) {
        appendLatency(valid);
      }
    } catch {
      // Probe failure is transient; next interval will retry
    } finally {
      setProbing(false);
    }
  }, [appendLatency]);

  // --- WebSocket ---
  const handleWsMessage = useCallback((data: WsProbeMessage) => {
    if (data.type === 'probe_result' && data.latency_ms !== null) {
      appendLatency([resultToRecord(data)]);
    }
  }, [appendLatency]);

  const wsUrl = `ws://localhost:19876/api/ws/dashboard`;
  const { send } = useWebSocket<WsProbeMessage>(wsUrl, handleWsMessage);

  // Subscribe to selected models via WebSocket (only when selectedModels change)
  const prevSelectedModelsRef = useRef<string>('');
  useEffect(() => {
    const key = JSON.stringify(selectedModels);
    if (key !== prevSelectedModelsRef.current) {
      prevSelectedModelsRef.current = key;
      send({ type: 'subscribe', providers: selectedModels });
    }
  }, [selectedModels, send]);

  // --- Auto-probe ---
  useEffect(() => {
    if (activeModels.length === 0) return;
    handleProbe(); // immediate first probe
    const interval = setInterval(handleProbe, AUTO_PROBE_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [activeModels.length]); // eslint-disable-line react-hooks/exhaustive-deps -- handleProbe is stable (useCallback with refs); length check handles model count change

  // --- KPIs (use store's latencyCache) ---
  const filteredRecords = useMemo(
    () => latencyCache.filter(r => r.provider === activeTab),
    [latencyCache, activeTab],
  );

  const kpis = useMemo(() => {
    const latencies = filteredRecords.map(r => r.latency_ms).sort((a, b) => a - b);
    const onlineCount = filteredRecords.filter(r => r.success).length;
    return {
      monitored: activeModels.length,
      p50: latencies.length > 0 ? latencies[Math.floor(latencies.length * 0.5)] : 0,
      p90: latencies.length > 0 ? latencies[Math.floor(latencies.length * 0.9)] : 0,
      onlineRate: filteredRecords.length > 0 ? (onlineCount / filteredRecords.length * 100) : 100,
    };
  }, [filteredRecords, activeModels.length]);

  // --- Model table data ---
  const modelRows = useMemo(() => {
    return activeModels.map(mname => {
      const modelRecords = filteredRecords.filter(r => r.model === mname);
      const last = modelRecords[modelRecords.length - 1];
      const mlatencies = modelRecords.map(r => r.latency_ms).sort((a, b) => a - b);
      return {
        model: mname,
        lastLatency: last?.latency_ms ?? null,
        p50: mlatencies.length > 0 ? mlatencies[Math.floor(mlatencies.length * 0.5)] : null,
        p90: mlatencies.length > 0 ? mlatencies[Math.floor(mlatencies.length * 0.9)] : null,
        online: last?.success ?? null,
        records: modelRecords.length,
      };
    });
  }, [filteredRecords, activeModels]);

  // --- Probe handler for button click ---
  function onProbeClick() { handleProbe(); }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'auto', padding: 12 }}>
      {/* Error banner */}
      {error && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 12px', marginBottom: 8,
          borderRadius: 6, background: 'color-mix(in srgb, var(--danger) 15%, transparent)',
          color: 'var(--danger)', fontSize: 12,
        }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

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
        <Button size="sm" onClick={onProbeClick} disabled={probing || activeModels.length === 0}>
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
        <LatencyChart records={filteredRecords} />
      </div>

      {/* Model Table */}
      <div style={{ marginTop: 16 }}>
        <ModelTable rows={modelRows} />
      </div>
    </div>
  );
}
