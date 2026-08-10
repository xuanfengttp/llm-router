import { useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { useT } from '@/locales';

const PRESET_PROVIDERS: { name: string; endpoint: string }[] = [
  { name: 'OpenAI', endpoint: 'https://api.openai.com/v1' },
  { name: 'Anthropic', endpoint: 'https://api.anthropic.com/v1' },
  { name: 'Google', endpoint: 'https://generativelanguage.googleapis.com/v1' },
  { name: 'Groq', endpoint: 'https://api.groq.com/openai/v1' },
  { name: 'DeepSeek', endpoint: 'https://api.deepseek.com/v1' },
  { name: 'Azure', endpoint: 'https://YOUR_RESOURCE.openai.azure.com' },
  { name: 'Ollama', endpoint: 'http://localhost:11434/v1' },
  { name: 'LocalAI', endpoint: 'http://localhost:8080/v1' },
];

interface AddProviderDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

type TabKey = 'preset' | 'custom';

export function AddProviderDialog({ open, onClose, onCreated }: AddProviderDialogProps) {
  const [tab, setTab] = useState<TabKey>('preset');
  const [name, setName] = useState('');
  const [endpoint, setEndpoint] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = useT();

  if (!open) return null;

  function selectPreset(p: { name: string; endpoint: string }) {
    setName(p.name);
    setEndpoint(p.endpoint);
    setApiKey('');
    setTab('custom');
  }

  async function handleCreate() {
    if (!name.trim()) {
      setError(t('必填项：名称'));
      return;
    }
    if (!endpoint.trim()) {
      setError(t('必填项：Endpoint'));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.createProvider({
        name: name.trim(),
        endpoint: endpoint.trim(),
        api_key: apiKey || undefined,
      });
      onCreated();
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 100,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: 480,
          maxHeight: '80vh',
          overflow: 'auto',
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: 24,
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <span style={{ fontSize: 16, fontWeight: 600 }}>{t('添加 Provider 对话框标题')}</span>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: 4,
              display: 'flex',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid var(--border)' }}>
          {(['preset', 'custom'] as TabKey[]).map((tabKey) => (
            <button
              key={tabKey}
              onClick={() => setTab(tabKey)}
              style={{
                padding: '6px 16px',
                fontSize: 13,
                background: 'transparent',
                border: 'none',
                borderBottom: tab === tabKey ? '2px solid var(--accent)' : '2px solid transparent',
                color: tab === tabKey ? 'var(--text-primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: tab === tabKey ? 600 : 400,
              }}
            >
              {tabKey === 'preset' ? t('预置') : t('自定义')}
            </button>
          ))}
        </div>

        {/* Preset tab */}
        {tab === 'preset' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {PRESET_PROVIDERS.map((p) => (
              <div
                key={p.name}
                onClick={() => selectPreset(p)}
                style={{
                  padding: 12,
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  cursor: 'pointer',
                  background: 'var(--bg-primary)',
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{p.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2, wordBreak: 'break-all' }}>
                  {p.endpoint}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Custom tab */}
        {tab === 'custom' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t('名称')}</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('例如 OpenAI')}
                style={inputStyle}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t('Endpoint 地址')}</span>
              <input
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="https://api.openai.com/v1"
                style={inputStyle}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t('API Key')}</span>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                style={inputStyle}
              />
            </label>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 12 }}>{error}</div>
        )}

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
          <Button variant="outline" size="sm" onClick={onClose}>
            {t('取消')}
          </Button>
          <Button size="sm" onClick={handleCreate} disabled={saving}>
            {saving ? t('创建中...') : t('创建')}
          </Button>
        </div>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  height: 32,
  padding: '0 8px',
  borderRadius: 4,
  border: '1px solid var(--border)',
  background: 'var(--bg-primary)',
  color: 'var(--text-primary)',
  fontSize: 13,
  outline: 'none',
  width: '100%',
  boxSizing: 'border-box',
};
