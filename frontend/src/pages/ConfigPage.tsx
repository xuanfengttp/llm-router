import { useEffect, useState, useCallback } from 'react';
import { useAppStore } from '@/store/appStore';
import { api } from '@/lib/api';
import { ProviderSidebar } from './config/ProviderSidebar';
import { ProviderDetail } from './config/ProviderDetail';

export default function ConfigPage() {
  const { providers, setProviders, activeProvider, setActiveProvider } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProviders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listProviders();
      setProviders(data);
      if (!activeProvider && data.length > 0) {
        setActiveProvider(data[0].name);
      }
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [setProviders, activeProvider, setActiveProvider]);

  useEffect(() => { loadProviders(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedProvider = providers.find((p) => p.name === activeProvider) || null;

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <ProviderSidebar
        providers={providers}
        activeProvider={activeProvider}
        onSelect={setActiveProvider}
        onRefresh={loadProviders}
      />
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {loading && (
          <div style={{ color: 'var(--text-secondary)', padding: 16 }}>Loading...</div>
        )}
        {error && (
          <div style={{ color: 'var(--danger)', padding: 16 }}>{error}</div>
        )}
        {!loading && !error && selectedProvider && (
          <ProviderDetail
            provider={selectedProvider}
            onUpdate={loadProviders}
          />
        )}
        {!loading && !error && !selectedProvider && (
          <div
            style={{
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
            }}
          >
            Select a provider or add a new one
          </div>
        )}
      </div>
    </div>
  );
}
