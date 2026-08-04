import { useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { StatusDot } from '@/components/StatusDot';
import { AddProviderDialog } from './AddProviderDialog';
import type { ProviderConfigOut } from '@/lib/types';
import { api } from '@/lib/api';

const PRESET_CHIPS = ['OpenAI', 'Anthropic', 'Google', 'Groq', 'DeepSeek'];

interface ProviderSidebarProps {
  providers: ProviderConfigOut[];
  activeProvider: string | null;
  onSelect: (name: string) => void;
  onRefresh: () => void;
}

export function ProviderSidebar({
  providers,
  activeProvider,
  onSelect,
  onRefresh,
}: ProviderSidebarProps) {
  const [addOpen, setAddOpen] = useState(false);

  async function handleDelete(name: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm(`Delete provider "${name}"? This will also remove all its models.`)) return;
    try {
      await api.deleteProvider(name);
      onRefresh();
    } catch (err: unknown) {
      if (err instanceof Error) alert(err.message);
    }
  }

  return (
    <>
      <div
        style={{
          width: 240,
          minWidth: 240,
          background: 'var(--bg-secondary)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
          <Button size="sm" onClick={() => setAddOpen(true)} style={{ width: '100%' }}>
            <Plus size={14} /> Add Provider
          </Button>
        </div>

        {/* Preset chips */}
        <div style={{ padding: '8px 12px', display: 'flex', flexWrap: 'wrap', gap: 4, borderBottom: '1px solid var(--border)' }}>
          {PRESET_CHIPS.map((chip) => (
            <span
              key={chip}
              onClick={() => setAddOpen(true)}
              style={{
                display: 'inline-block',
                padding: '2px 8px',
                borderRadius: 12,
                fontSize: 11,
                background: 'var(--bg-hover)',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              {chip}
            </span>
          ))}
        </div>

        {/* Provider list */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {providers.map((p) => {
            const isActive = p.name === activeProvider;
            return (
              <div
                key={p.name}
                onClick={() => onSelect(p.name)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  cursor: 'pointer',
                  background: isActive ? 'color-mix(in srgb, var(--accent) 20%, transparent)' : 'transparent',
                  borderLeft: isActive ? '3px solid var(--accent)' : '3px solid transparent',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) (e.currentTarget as HTMLElement).style.background = 'var(--bg-hover)';
                }}
                onMouseLeave={(e) => {
                  if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent';
                }}
              >
                <StatusDot status={p.status} />
                <span
                  style={{
                    flex: 1,
                    fontSize: 12,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {p.name}
                </span>
                <button
                  onClick={(e) => handleDelete(p.name, e)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    padding: 2,
                    display: 'flex',
                    opacity: 0.6,
                  }}
                  title="Delete provider"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            );
          })}

          {providers.length === 0 && (
            <div
              style={{
                padding: 16,
                color: 'var(--text-secondary)',
                fontSize: 12,
                textAlign: 'center',
              }}
            >
              No providers configured
            </div>
          )}
        </div>
      </div>

      <AddProviderDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={() => {
          setAddOpen(false);
          onRefresh();
        }}
      />
    </>
  );
}
