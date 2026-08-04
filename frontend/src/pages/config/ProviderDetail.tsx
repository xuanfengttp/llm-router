import { useState } from 'react';
import { Wifi, Eye, EyeOff, Copy, Check, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { StatusDot } from '@/components/StatusDot';
import { ModelTable } from './ModelTable';
import { api } from '@/lib/api';
import type { ProviderConfigOut } from '@/lib/types';
import type { NewModelFields } from './ModelTable';

interface ProviderDetailProps {
  provider: ProviderConfigOut;
  onUpdate: () => void;
}

export function ProviderDetail({ provider, onUpdate }: ProviderDetailProps) {
  const [showKey, setShowKey] = useState(false);
  const [apiKeyValue, setApiKeyValue] = useState('');
  const [savingKey, setSavingKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const maskedKey = provider.endpoint ? '********' : '(not set)';

  async function handleSaveKey() {
    if (!apiKeyValue.trim()) return;
    setSavingKey(true);
    try {
      await api.updateApiKey(provider.name, apiKeyValue);
      setApiKeyValue('');
      setShowKey(false);
      onUpdate();
    } catch {
      // error handled by refresh
    } finally {
      setSavingKey(false);
    }
  }

  async function handleTestConnection() {
    setTesting(true);
    setTestResult(null);
    try {
      // Use the probe endpoint as test connection
      await api.probe([provider.name], []);
      setTestResult('Connection successful');
    } catch (err: unknown) {
      if (err instanceof Error) setTestResult(`Failed: ${err.message}`);
      else setTestResult('Failed');
    } finally {
      setTesting(false);
    }
  }

  function handleCopyEndpoint() {
    navigator.clipboard.writeText(provider.endpoint);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleAddModel(fields: NewModelFields) {
    await api.addModel(provider.name, {
      name: fields.name,
      deployment: fields.deployment,
      context_window: fields.context_window,
    } as { name: string; deployment?: string; context_window?: number });
    onUpdate();
  }

  async function handleRemoveModel(mname: string) {
    await api.removeModel(provider.name, mname);
    onUpdate();
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <StatusDot status={provider.status} size={12} />
        <span style={{ fontSize: 18, fontWeight: 600 }}>{provider.name}</span>
        <span
          style={{
            fontSize: 11,
            padding: '1px 8px',
            borderRadius: 10,
            background:
              provider.status === 'online' ? 'color-mix(in srgb, var(--success) 15%, transparent)' :
              provider.status === 'offline' ? 'color-mix(in srgb, var(--danger) 15%, transparent)' :
              provider.status === 'degraded' ? 'color-mix(in srgb, var(--warning) 15%, transparent)' :
              'color-mix(in srgb, var(--text-secondary) 15%, transparent)',
            color:
              provider.status === 'online' ? 'var(--success)' :
              provider.status === 'offline' ? 'var(--danger)' :
              provider.status === 'degraded' ? 'var(--warning)' :
              'var(--text-secondary)',
          }}
        >
          {provider.status || 'unknown'}
        </span>
      </div>

      {/* Endpoint */}
      <div
        style={{
          padding: 12,
          background: 'var(--bg-secondary)',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 60 }}>Endpoint</span>
        <code
          style={{
            flex: 1,
            fontSize: 12,
            color: 'var(--text-primary)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {provider.endpoint}
        </code>
        <button
          onClick={handleCopyEndpoint}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: 4,
            display: 'flex',
          }}
          title="Copy endpoint"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      </div>

      {/* API Key */}
      <div
        style={{
          padding: 12,
          background: 'var(--bg-secondary)',
          borderRadius: 6,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 60 }}>API Key</span>
          <code
            style={{
              flex: 1,
              fontSize: 12,
              color: 'var(--text-primary)',
            }}
          >
            {showKey ? apiKeyValue || maskedKey : maskedKey}
          </code>
          <button
            onClick={() => setShowKey(!showKey)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
            }}
            title={showKey ? 'Hide' : 'Show'}
          >
            {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="password"
            value={apiKeyValue}
            onChange={(e) => setApiKeyValue(e.target.value)}
            placeholder="Enter new API key..."
            style={{
              flex: 1,
              height: 30,
              padding: '0 8px',
              borderRadius: 4,
              border: '1px solid var(--border)',
              background: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              fontSize: 12,
              outline: 'none',
            }}
          />
          <Button size="sm" onClick={handleSaveKey} disabled={savingKey || !apiKeyValue.trim()}>
            {savingKey ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      {/* Test Connection */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Button
          size="sm"
          variant="outline"
          onClick={handleTestConnection}
          disabled={testing}
        >
          {testing ? (
            <>
              <RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} /> Testing...
            </>
          ) : (
            <>
              <Wifi size={12} /> Test Connection
            </>
          )}
        </Button>
        {testResult && (
          <span
            style={{
              fontSize: 12,
              color: testResult.includes('Failed') ? 'var(--danger)' : 'var(--success)',
            }}
          >
            {testResult}
          </span>
        )}
      </div>

      {/* Divider */}
      <div style={{ borderTop: '1px solid var(--border)' }} />

      {/* Models */}
      <ModelTable
        models={provider.models}
        onAdd={handleAddModel}
        onRemove={handleRemoveModel}
      />
    </div>
  );
}
