import { useState } from 'react';
import { Trash2, Plus, X, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ModelConfigOut } from '@/lib/types';
import { useT } from '@/locales';

interface ModelTableProps {
  models: ModelConfigOut[];
  onAdd: (model: NewModelFields) => Promise<void>;
  onRemove: (name: string) => Promise<void>;
}

export interface NewModelFields {
  name: string;
  deployment: string;
  context_window: number;
  cost_input_1k: number;
  cost_output_1k: number;
}

const DEPLOY_TRANSLATE: Record<string, string> = { cloud: '云端', local: '本地', hybrid: '混合' };

export function ModelTable({ models, onAdd, onRemove }: ModelTableProps) {
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDeployment, setNewDeployment] = useState('cloud');
  const [newContext, setNewContext] = useState('4096');
  const [newCostIn, setNewCostIn] = useState('');
  const [newCostOut, setNewCostOut] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = useT();
  const DEPLOYMENTS = ['cloud', 'local', 'hybrid'];

  async function handleAdd() {
    if (!newName.trim()) return;
    setSaving(true);
    try {
      await onAdd({
        name: newName.trim(),
        deployment: newDeployment,
        context_window: parseInt(newContext, 10) || 4096,
        cost_input_1k: parseFloat(newCostIn) || 0,
        cost_output_1k: parseFloat(newCostOut) || 0,
      });
      setNewName('');
      setNewDeployment('cloud');
      setNewContext('4096');
      setNewCostIn('');
      setNewCostOut('');
      setAdding(false);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError(t('添加模型失败'));
    } finally {
      setSaving(false);
    }
  }

  function cancelAdd() {
    setAdding(false);
    setNewName('');
    setNewDeployment('cloud');
    setNewContext('4096');
    setNewCostIn('');
    setNewCostOut('');
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>{t('模型 (N个)')} ({models.length})</span>
          {error && <span style={{ fontSize: 11, color: 'var(--danger)' }}>{error}</span>}
        </div>
        {!adding && (
          <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
            <Plus size={12} /> {t('添加模型')}
          </Button>
        )}
      </div>

      {/* Inline add form */}
      {adding && (
        <div
          style={{
            padding: 12,
            marginBottom: 8,
            border: '1px solid var(--accent)',
            borderRadius: 6,
            background: 'var(--bg-primary)',
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <label style={formLabelStyle}>
              <span>{t('Name *')}</span>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="gpt-4"
                style={formInputStyle}
              />
            </label>
            <label style={formLabelStyle}>
              <span>{t('部署方式')}</span>
              <select
                value={newDeployment}
                onChange={(e) => setNewDeployment(e.target.value)}
                style={formInputStyle}
              >
                {DEPLOYMENTS.map((d) => (
                  <option key={d} value={d}>{t(DEPLOY_TRANSLATE[d])}</option>
                ))}
              </select>
            </label>
            <label style={formLabelStyle}>
              <span>{t('上下文窗口')}</span>
              <input
                value={newContext}
                onChange={(e) => setNewContext(e.target.value)}
                type="number"
                style={formInputStyle}
              />
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <label style={formLabelStyle}>
                <span>{t('输入成本 ($/1k)')}</span>
                <input
                  value={newCostIn}
                  onChange={(e) => setNewCostIn(e.target.value)}
                  type="number"
                  step="0.0001"
                  placeholder="0.001"
                  style={formInputStyle}
                />
              </label>
              <label style={formLabelStyle}>
                <span>{t('输出成本 ($/1k)')}</span>
                <input
                  value={newCostOut}
                  onChange={(e) => setNewCostOut(e.target.value)}
                  type="number"
                  step="0.0001"
                  placeholder="0.002"
                  style={formInputStyle}
                />
              </label>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 10 }}>
            <Button size="sm" variant="ghost" onClick={cancelAdd}>
              <X size={12} /> {t('取消')}
            </Button>
            <Button size="sm" onClick={handleAdd} disabled={saving || !newName.trim()}>
              {saving ? t('添加中...') : (
                <>
                  <Check size={12} /> {t('添加')}
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Models table */}
      {models.length > 0 ? (
        <div style={{ border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)' }}>
                <th style={thStyle}>{t('名称')}</th>
                <th style={thStyle}>{t('部署方式')}</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>{t('上下文')}</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>{t('成本 (入/出 $1k)')}</th>
                <th style={{ ...thStyle, width: 40 }}></th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr
                  key={m.name}
                  style={{ borderTop: '1px solid var(--border)' }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background = 'transparent';
                  }}
                >
                  <td style={tdStyle}>
                    <span style={{ fontWeight: 500 }}>{m.name}</span>
                    {m.tags.length > 0 && (
                      <span style={{ marginLeft: 6 }}>
                        {m.tags.map((t) => (
                          <span
                            key={t}
                            style={{
                              display: 'inline-block',
                              padding: '1px 6px',
                              borderRadius: 3,
                              fontSize: 10,
                              background: 'var(--bg-card)',
                              color: 'var(--text-secondary)',
                              marginRight: 3,
                            }}
                          >
                            {t}
                          </span>
                        ))}
                      </span>
                    )}
                  </td>
                  <td style={tdStyle}>
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '1px 8px',
                        borderRadius: 3,
                        fontSize: 11,
                        background: m.deployment === 'cloud' ? 'color-mix(in srgb, var(--accent) 15%, transparent)' :
                          m.deployment === 'local' ? 'color-mix(in srgb, var(--success) 15%, transparent)' :
                          'color-mix(in srgb, var(--warning) 15%, transparent)',
                        color: m.deployment === 'cloud' ? 'var(--accent)' :
                          m.deployment === 'local' ? 'var(--success)' : 'var(--warning)',
                      }}
                    >
                      {t(DEPLOY_TRANSLATE[m.deployment] || m.deployment)}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>
                    {m.context_window.toLocaleString()}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {m.cost_input_1k.toFixed(4)} / {m.cost_output_1k.toFixed(4)}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'center' }}>
                    <button
                      onClick={async () => {
                        if (!confirm(t('确定删除模型 "{}"？').replace('{}', m.name))) return;
                        try {
                          await onRemove(m.name);
                        } catch (err: unknown) {
                          if (err instanceof Error) alert(err.message);
                        }
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                        padding: 4,
                        display: 'flex',
                      }}
                      title={t('删除模型')}
                    >
                      <Trash2 size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div
          style={{
            padding: 24,
            textAlign: 'center',
            color: 'var(--text-secondary)',
            fontSize: 12,
            border: '1px solid var(--border)',
            borderRadius: 6,
          }}
        >
          {t('暂无模型')}
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '6px 10px',
  fontSize: 11,
  fontWeight: 600,
  color: 'var(--text-secondary)',
  border: 'none',
};

const tdStyle: React.CSSProperties = {
  padding: '6px 10px',
  border: 'none',
};

const formLabelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
  fontSize: 11,
  color: 'var(--text-secondary)',
};

const formInputStyle: React.CSSProperties = {
  height: 28,
  padding: '0 6px',
  borderRadius: 4,
  border: '1px solid var(--border)',
  background: 'var(--bg-card)',
  color: 'var(--text-primary)',
  fontSize: 12,
  outline: 'none',
  width: '100%',
  boxSizing: 'border-box',
};
