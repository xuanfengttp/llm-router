import { useT } from '@/locales';

interface KpiStatCardsProps {
  kpis: { monitored: number; p50: number; p90: number; onlineRate: number };
}

export function KpiStatCards({ kpis }: KpiStatCardsProps) {
  const t = useT();
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
      <KpiCard label={t('监控模型数')} value={kpis.monitored} />
      <KpiCard label={t('P50 延迟')} value={`${kpis.p50.toFixed(0)}ms`} />
      <KpiCard label={t('P90 延迟')} value={`${kpis.p90.toFixed(0)}ms`} />
      <KpiCard label={t('在线率')} value={`${kpis.onlineRate.toFixed(1)}%`} />
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
