import type { ProviderConfigOut } from '@/lib/types';

interface ProviderTabsProps {
  providers: ProviderConfigOut[];
  activeTab: string;
  onSelect: (name: string) => void;
}

export function ProviderTabs({ providers, activeTab, onSelect }: ProviderTabsProps) {
  if (providers.length === 0) {
    return (
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '8px 0' }}>
        No providers configured. Go to Config to add one.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
      {providers.map((p) => (
        <button
          key={p.name}
          onClick={() => onSelect(p.name)}
          style={{
            padding: '4px 14px',
            fontSize: 12,
            fontWeight: 500,
            borderRadius: 4,
            border: '1px solid var(--border)',
            cursor: 'pointer',
            background: activeTab === p.name ? 'var(--accent)' : 'var(--bg-card)',
            color: activeTab === p.name ? '#fff' : 'var(--text-primary)',
          }}
        >
          {p.name}
        </button>
      ))}
    </div>
  );
}
