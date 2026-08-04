import { useState } from 'react';

type LogTab = 'operations' | 'model_switch' | 'audit';

interface LogEntry {
  id: number;
  timestamp: string;
  [key: string]: string | number;
}

const OP_LOGS: LogEntry[] = Array.from({ length: 12 }, (_, i) => ({
  id: i,
  timestamp: new Date(Date.now() - i * 60000).toISOString(),
  type: ['route', 'probe', 'score', 'dispatch'][i % 4],
  detail: `Request #${1000 + i} processed`,
  duration: `${(Math.random() * 500 + 50).toFixed(0)}ms`,
}));

const SWITCH_LOGS: LogEntry[] = Array.from({ length: 8 }, (_, i) => ({
  id: i,
  timestamp: new Date(Date.now() - i * 120000).toISOString(),
  from: ['gpt-4', 'claude-3', 'gemini-pro', 'deepseek-v3'][i % 4],
  to: ['claude-3', 'gemini-pro', 'gpt-4', 'deepseek-v3'][(i + 1) % 4],
  reason: ['latency spike', 'cost optimization', 'quality degradation', 'manual override'][i % 4],
}));

const AUDIT_LOGS: LogEntry[] = Array.from({ length: 10 }, (_, i) => ({
  id: i,
  timestamp: new Date(Date.now() - i * 300000).toISOString(),
  action: ['provider.add', 'model.delete', 'settings.update', 'api_key.change'][i % 4],
  user: 'admin',
  detail: `Changed configuration #${i + 1}`,
}));

export default function LogsPage() {
  const [tab, setTab] = useState<LogTab>('operations');

  const tabs: { key: LogTab; label: string }[] = [
    { key: 'operations', label: 'Operations' },
    { key: 'model_switch', label: 'Model Switch' },
    { key: 'audit', label: 'Audit' },
  ];

  function renderTable(logs: LogEntry[], columns: string[]) {
    return (
      <div style={{ border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)' }}>
              {columns.map(col => (
                <th key={col} style={{ textAlign: 'left', padding: '6px 10px', fontSize: 11, fontWeight: 600,
                  color: 'var(--text-secondary)', border: 'none' }}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {logs.map(row => (
              <tr key={row.id} style={{ borderTop: '1px solid var(--border)' }}>
                {columns.map(col => (
                  <td key={col} style={{ padding: '6px 10px', border: 'none', fontSize: 12 }}>
                    {col === 'Timestamp'
                      ? <code style={{ fontSize: 10 }}>{new Date(row.timestamp as string).toLocaleTimeString()}</code>
                      : String(row[col.toLowerCase().replace(' ', '_')] ?? '-')
                    }
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'auto', padding: 12 }}>
      <span style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Logs</span>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 12, borderBottom: '1px solid var(--border)' }}>
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: '6px 16px', fontSize: 12, border: 'none', background: 'none',
              color: tab === t.key ? 'var(--text-primary)' : 'var(--text-secondary)',
              borderBottom: tab === t.key ? '2px solid var(--accent)' : '2px solid transparent',
              cursor: 'pointer', fontWeight: tab === t.key ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Log tables */}
      {tab === 'operations' && renderTable(OP_LOGS, ['Timestamp', 'Type', 'Detail', 'Duration'])}
      {tab === 'model_switch' && renderTable(SWITCH_LOGS, ['Timestamp', 'From', 'To', 'Reason'])}
      {tab === 'audit' && renderTable(AUDIT_LOGS, ['Timestamp', 'Action', 'User', 'Detail'])}
    </div>
  );
}
