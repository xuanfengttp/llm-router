import type { ModelConfigOut } from '@/lib/types';

interface ModelChipGridProps {
  models: ModelConfigOut[];
  selected: string[];
  onToggle: (model: string) => void;
}

export function ModelChipGrid({ models, selected, onToggle }: ModelChipGridProps) {
  if (models.length === 0) {
    return null;
  }

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
      {models.map((m) => {
        const isSelected = selected.includes(m.name);
        return (
          <button
            key={m.name}
            onClick={() => onToggle(m.name)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              padding: '2px 10px',
              fontSize: 11,
              borderRadius: 14,
              border: isSelected ? '1px solid var(--accent)' : '1px solid var(--border)',
              cursor: 'pointer',
              background: isSelected ? 'var(--accent)' : 'transparent',
              color: isSelected ? '#fff' : 'var(--text-primary)',
            }}
          >
            {m.name}
          </button>
        );
      })}
    </div>
  );
}
