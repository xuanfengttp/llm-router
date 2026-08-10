interface ModelRow {
  model: string;
  lastLatency: number | null;
  p50: number | null;
  p90: number | null;
  online: boolean | null;
  records: number;
}

interface ModelTableProps {
  rows: ModelRow[];
}

import { useT } from '@/locales';

export function ModelTable({ rows }: ModelTableProps) {
  const t = useT();
  if (rows.length === 0) {
    return (
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '8px 0' }}>
        {t('请选择上方模型查看延迟数据')}
      </div>
    );
  }

  const HEADERS = [t('模型'), t('最近延迟'), t('P50'), t('P90'), t('在线状态'), t('记录数')];

  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>{t('模型延迟详情')}</div>
      <div style={{
        overflowX: 'auto',
        border: '1px solid var(--border)',
        borderRadius: 6,
      }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 12,
        }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)' }}>
              {HEADERS.map((h) => (
                <th
                  key={h}
                  style={{
                    padding: '6px 12px',
                    textAlign: 'left',
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    fontSize: 11,
                    borderBottom: '1px solid var(--border)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.model}
                style={{ borderBottom: '1px solid var(--border)' }}
              >
                <td style={{ padding: '6px 12px', fontWeight: 500 }}>{row.model}</td>
                <td style={{ padding: '6px 12px' }}>
                  {row.lastLatency !== null ? `${row.lastLatency.toFixed(0)}ms` : '-'}
                </td>
                <td style={{ padding: '6px 12px' }}>
                  {row.p50 !== null ? `${row.p50.toFixed(0)}ms` : '-'}
                </td>
                <td style={{ padding: '6px 12px' }}>
                  {row.p90 !== null ? `${row.p90.toFixed(0)}ms` : '-'}
                </td>
                <td style={{ padding: '6px 12px' }}>
                  {row.online === true ? (
                    <span style={{ color: 'var(--success)' }}>{t('在线')}</span>
                  ) : row.online === false ? (
                    <span style={{ color: 'var(--danger)' }}>{t('离线')}</span>
                  ) : (
                    '-'
                  )}
                </td>
                <td style={{ padding: '6px 12px', color: 'var(--text-secondary)' }}>
                  {row.records}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
