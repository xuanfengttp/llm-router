import { useState } from 'react';
import { Wifi, Eye, EyeOff, Copy, Check, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { StatusDot } from '@/components/StatusDot';
import { ModelTable } from './ModelTable';
import { api } from '@/lib/api';
import type { ProviderConfigOut } from '@/lib/types';
import type { NewModelFields } from './ModelTable';
import { useT } from '@/locales';

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
  const t = useT();

  const maskedKey = provider.endpoint ? '********' : t('未设置');

  async function handleSaveKey() {
    if (!apiKeyValue.trim()) return;
    setSavingKey(true);
    try {
      await api.updateApiKey(provider.name, apiKeyValue);
      setApiKeyValue('');
      setShowKey(false);
      onUpdate();
    } catch (err: unknown) {
      if (err instanceof Error) setTestResult(`${t('保存失败: ')}${err.message}`);
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
      setTestResult(t('连接成功'));
    } catch (err: unknown) {
      if (err instanceof Error) setTestResult(`${t('失败: ')}${err.message}`);
      else setTestResult(t('连接失败'));
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
      cost_input_1k: fields.cost_input_1k,
      cost_output_1k: fields.cost_output_1k,
    });
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
          {provider.status || t('未知')}
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
        <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 60 }}>{t('Endpoint')}</span>
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
          title={t('复制 Endpoint')}
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
          <span style={{ fontSize: 12, color: 'var(--text-secondary)', minWidth: 60 }}>{t('API 密钥')}</span>
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
            title={showKey ? t('隐藏') : t('显示')}
          >
            {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="password"
            value={apiKeyValue}
            onChange={(e) => setApiKeyValue(e.target.value)}
            placeholder={t('输入新的 API Key...')}
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
            {savingKey ? t('保存中...') : t('保存')}
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
              <RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} /> {t('测试中...')}
            </>
          ) : (
            <>
              <Wifi size={12} /> {t('测试连接')}
            </>
          )}
        </Button>
        {testResult && (
          <span
            style={{
              fontSize: 12,
              color: testResult.includes(t('连接失败')) ? 'var(--danger)' : 'var(--success)',
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
