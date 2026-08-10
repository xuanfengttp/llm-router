import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { useAppStore } from '@/store/appStore';
import { Plus, RefreshCw, XCircle, RotateCcw, AlertCircle } from 'lucide-react';
import type { TaskOut } from '@/lib/types';
import { useT } from '@/locales';

const STATUS_TRANSLATE: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'var(--warning)',
  running: 'var(--accent)',
  completed: 'var(--success)',
  failed: 'var(--danger)',
};

export default function TasksPage() {
  const { providers } = useAppStore();
  const [tasks, setTasks] = useState<TaskOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const [targetModel, setTargetModel] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const t = useT();

  const loadTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listTasks(50, 0);
      setTasks(data);
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadTasks(); }, [loadTasks]);

  async function handleCreate() {
    if (!prompt.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.createTask({ prompt: prompt.trim(), target_model: targetModel || undefined });
      setPrompt('');
      setTargetModel('');
      await loadTasks();
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
    } finally { setSubmitting(false); }
  }

  async function handleCancel(taskId: string) {
    try { await api.cancelTask(taskId); await loadTasks(); }
    catch (e: unknown) { if (e instanceof Error) setError(e.message); }
  }

  async function handleRetry(taskId: string) {
    try { await api.retryTask(taskId); await loadTasks(); }
    catch (e: unknown) { if (e instanceof Error) setError(e.message); }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontSize: 16, fontWeight: 600 }}>{t('任务')}</span>
        <Button size="sm" variant="outline" onClick={loadTasks} disabled={loading}>
          <RefreshCw size={12} /> {t('刷新')}
        </Button>
      </div>

      {error && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', marginBottom: 8,
          borderRadius: 6, background: 'color-mix(in srgb, var(--danger) 15%, transparent)',
          color: 'var(--danger)', fontSize: 12 }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* Create Task Form */}
      <div style={{ padding: 12, background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 6, marginBottom: 12 }}>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder={t('输入你的提示词...')}
          rows={3}
          style={{ width: '100%', padding: 8, borderRadius: 4, border: '1px solid var(--border)',
            background: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: 12,
            outline: 'none', resize: 'vertical', boxSizing: 'border-box', marginBottom: 8 }}
        />
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select
            value={targetModel}
            onChange={e => setTargetModel(e.target.value)}
            style={{ height: 28, padding: '0 6px', borderRadius: 4, border: '1px solid var(--border)',
              background: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: 12, outline: 'none', flex: 1 }}
          >
            <option value="">{t('任意模型')}</option>
            {providers.flatMap(p => p.models.map(m => (
              <option key={`${p.name}/${m.name}`} value={`${p.name}/${m.name}`}>{p.name}/{m.name}</option>
            )))}
          </select>
          <Button size="sm" onClick={handleCreate} disabled={submitting || !prompt.trim()}>
            <Plus size={12} /> {submitting ? t('提交中...') : t('提交')}
          </Button>
        </div>
      </div>

      {/* Task List */}
      {loading ? (
        <div style={{ color: 'var(--text-secondary)', padding: 24, textAlign: 'center' }}>{t('加载中...')}</div>
      ) : tasks.length > 0 ? (
        <div style={{ border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)' }}>
                <th style={thStyle}>{t('Task ID')}</th>
                <th style={thStyle}>{t('提示词')}</th>
                <th style={thStyle}>{t('目标模型')}</th>
                <th style={thStyle}>{t('状态')}</th>
                <th style={{ ...thStyle, width: 80 }}>{t('操作')}</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map(task => (
                <tr key={task.task_id} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={tdStyle}>
                    <code style={{ fontSize: 11 }}>{task.task_id?.slice(0, 8)}...</code>
                  </td>
                  <td style={tdStyle}>
                    <span style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'inline-block' }}>
                      {task.prompt || '-'}
                    </span>
                  </td>
                  <td style={tdStyle}>{task.target_model || t('自动')}</td>
                  <td style={tdStyle}>
                    <span style={{ color: STATUS_COLORS[task.status] || 'var(--text-secondary)', fontWeight: 500 }}>
                      {t(STATUS_TRANSLATE[task.status] || task.status)}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, display: 'flex', gap: 4 }}>
                    {(task.status === 'pending' || task.status === 'running') && (
                      <button onClick={() => handleCancel(task.task_id)} title={t('取消')}
                        style={iconBtnStyle}><XCircle size={14} /></button>
                    )}
                    {task.status === 'failed' && (
                      <button onClick={() => handleRetry(task.task_id)} title={t('重试')}
                        style={iconBtnStyle}><RotateCcw size={14} /></button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 12,
          border: '1px solid var(--border)', borderRadius: 6 }}>
          {t('暂无任务，在上方输入提示词创建')}
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: 'left', padding: '6px 10px', fontSize: 11, fontWeight: 600,
  color: 'var(--text-secondary)', border: 'none',
};

const tdStyle: React.CSSProperties = {
  padding: '6px 10px', border: 'none',
};

const iconBtnStyle: React.CSSProperties = {
  background: 'none', border: 'none', color: 'var(--text-secondary)',
  cursor: 'pointer', padding: 2, display: 'flex',
};
