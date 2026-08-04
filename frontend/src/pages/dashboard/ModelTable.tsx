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

export function ModelTable({ rows }: ModelTableProps) {
  if (rows.length === 0) {
    return (
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '8px 0' }}>
        No models selected. Select models above to see latency details.
      </div>
    );
  }

  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Model Latency Details</div>
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
              {['Model', 'Last Latency', 'P50', 'P90', 'Online', 'Records'].map((h) => (
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
                    <span style={{ color: 'var(--success)' }}>Online</span>
                  ) : row.online === false ? (
                    <span style={{ color: 'var(--danger)' }}>Offline</span>
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
