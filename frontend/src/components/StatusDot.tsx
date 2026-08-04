interface StatusDotProps {
  status: string;
  size?: number;
}

export function StatusDot({ status, size = 8 }: StatusDotProps) {
  const color =
    status === 'online' ? 'var(--success)' :
    status === 'degraded' ? 'var(--warning)' :
    status === 'offline' ? 'var(--danger)' :
    'var(--text-secondary)';

  return (
    <span
      style={{
        display: 'inline-block',
        width: size,
        height: size,
        borderRadius: '50%',
        background: color,
        flexShrink: 0,
      }}
    />
  );
}
