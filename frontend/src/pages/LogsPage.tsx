import { useState } from 'react';
import { useT } from '@/locales';

type LogTab = 'operations' | 'model_switch' | 'audit';

interface LogEntry {
  id: number;
  timestamp: string;
  [key: string]: string | number;
}

const LABEL_MAP: Record<string, string> = {
  route: '路由', probe: '探测', score: '评分', dispatch: '调度',
  'latency spike': '延迟飙升', 'cost optimization': '成本优化',
  'quality degradation': '质量下降', 'manual override': '手动覆盖',
  'provider.add': 'provider.add', 'model.delete': 'model.delete',
  'settings.update': 'settings.update', 'api_key.change': 'api_key.change',
};

const OP_LOGS: LogEntry[] = Array.from({ length: 12 }, (_, i) => ({
  id: i,
  timestamp: new Date(Date.now() - i * 60000).toISOString(),
  type: ['route', 'probe', 'score', 'dispatch'][i % 4],
  detail: `请求 #${1000 + i} 已处理`,
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
  detail: `配置 #${i + 1} 已变更`,
}));

export default function LogsPage() {
  const [tab, setTab] = useState<LogTab>('operations');
  const t = useT();

  const tabs: { key: LogTab; label: string }[] = [
    { key: 'operations', label: t('操作日志') },
    { key: 'model_switch', label: t('模型切换') },
    { key: 'audit', label: t('审计') },
  ];

  const COL_MAP: Record<string, string> = {
    Timestamp: t('时间戳'), Type: t('类型'), Detail: t('详情'),
    Duration: t('耗时'), From: t('来源'), To: t('目标'),
    Reason: t('原因'), Action: t('行为'), User: t('用户'),
  };

  function renderTable(logs: LogEntry[], columns: string[]) {
    return (
      <div style={{ border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)' }}>
              {columns.map(col => (
                <th key={col} style={{ textAlign: 'left', padding: '6px 10px', fontSize: 11, fontWeight: 600,
                  color: 'var(--text-secondary)', border: 'none' }}>{COL_MAP[col] || col}</th>
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
                      : String(LABEL_MAP[row[col.toLowerCase().replace(' ', '_')] as string] ?? row[col.toLowerCase().replace(' ', '_')] ?? '-')
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
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 12 }}>
      <span style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>{t('日志')}</span>

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
