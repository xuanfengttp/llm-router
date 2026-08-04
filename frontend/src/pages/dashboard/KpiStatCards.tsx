interface KpiStatCardsProps {
  kpis: { monitored: number; p50: number; p90: number; onlineRate: number };
}

export function KpiStatCards({ kpis }: KpiStatCardsProps) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
      <KpiCard label="Models Monitored" value={kpis.monitored} />
      <KpiCard label="P50 Latency" value={`${kpis.p50.toFixed(0)}ms`} />
      <KpiCard label="P90 Latency" value={`${kpis.p90.toFixed(0)}ms`} />
      <KpiCard label="Online Rate" value={`${kpis.onlineRate.toFixed(1)}%`} />
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{
      padding: '12px 16px',
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 6,
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 600, color: 'var(--text-primary)' }}>{value}</div>
    </div>
  );
}
