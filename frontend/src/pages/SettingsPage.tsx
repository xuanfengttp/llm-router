import { useState, useEffect, useRef } from 'react';
import { useAppStore } from '@/store/appStore';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { AlertCircle, Check } from 'lucide-react';
import type { SettingsOut } from '@/lib/types';

type SettingsSection = 'strategy' | 'params' | 'time' | 'appearance' | 'data' | 'about';

const SECTIONS: { key: SettingsSection; label: string }[] = [
  { key: 'strategy', label: 'Strategy' },
  { key: 'params', label: 'Params' },
  { key: 'time', label: 'Time' },
  { key: 'appearance', label: 'Appearance' },
  { key: 'data', label: 'Data' },
  { key: 'about', label: 'About' },
];

export default function SettingsPage() {
  const { settings, setSettings: updateStoreSettings, setTheme: updateTheme } = useAppStore();
  const [section, setSection] = useState<SettingsSection>('strategy');
  const [form, setForm] = useState<SettingsOut>(settings);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => { setForm(settings); }, [settings]);

  useEffect(() => {
    return () => clearTimeout(successTimerRef.current);
  }, []);

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const updated = await api.updateSettings(form);
      updateStoreSettings(updated);
      // Propagate theme change if needed
      if (updated.theme !== form.theme) {
        updateTheme(updated.theme as 'dark' | 'light');
      }
      setSuccess(true);
      clearTimeout(successTimerRef.current);
      successTimerRef.current = setTimeout(() => setSuccess(false), 2000);
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
    } finally { setSaving(false); }
  }

  function update<K extends keyof SettingsOut>(key: K, value: SettingsOut[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
  }

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Sidebar */}
      <div style={{ width: 180, borderRight: '1px solid var(--border)', padding: '8px 0', overflow: 'auto' }}>
        {SECTIONS.map(s => (
          <button
            key={s.key}
            onClick={() => setSection(s.key)}
            style={{
              display: 'block', width: '100%', textAlign: 'left', padding: '8px 16px',
              fontSize: 12, border: 'none', cursor: 'pointer',
              background: section === s.key ? 'color-mix(in srgb, var(--accent) 12%, transparent)' : 'transparent',
              color: section === s.key ? 'var(--accent)' : 'var(--text-secondary)',
              fontWeight: section === s.key ? 600 : 400,
            }}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Panel */}
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <span style={{ fontSize: 16, fontWeight: 600 }}>
            {SECTIONS.find(s => s.key === section)?.label}
          </span>
          {section !== 'about' && (
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save'}
            </Button>
          )}
        </div>

        {error && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', marginBottom: 8,
            borderRadius: 6, background: 'color-mix(in srgb, var(--danger) 15%, transparent)',
            color: 'var(--danger)', fontSize: 12 }}>
            <AlertCircle size={14} /> {error}
          </div>
        )}
        {success && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', marginBottom: 8,
            borderRadius: 6, background: 'color-mix(in srgb, var(--success) 15%, transparent)',
            color: 'var(--success)', fontSize: 12 }}>
            <Check size={14} /> Settings saved
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {section === 'strategy' && (
            <RadioGroupField label="Routing Strategy" value={form.strategy}
              options={[
                { value: 'baseline', label: 'Baseline — simple round-robin' },
                { value: 'cost_optimized', label: 'Cost Optimized — cheapest first' },
                { value: 'predictive', label: 'Predictive — ML-driven selection' },
              ]}
              onChange={v => update('strategy', v as SettingsOut['strategy'])} />
          )}

          {section === 'params' && (
            <>
              <SliderField label="Latency Redline (ms)" value={form.latency_redline_ms}
                min={500} max={30000} step={100}
                onChange={v => update('latency_redline_ms', v)} />
              <SliderField label="Predictability Threshold" value={form.predictability_threshold}
                min={0.05} max={2.0} step={0.05}
                onChange={v => update('predictability_threshold', v)} />
              <NumberField label="Cycle Seconds" value={form.cycle_seconds}
                onChange={v => update('cycle_seconds', v)} />
              <NumberField label="Max Retries" value={form.max_retries}
                onChange={v => update('max_retries', v)} />
            </>
          )}

          {section === 'time' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <NumberField label="Night Start (hour)" value={form.night_start} min={0} max={23}
                  onChange={v => update('night_start', v)} />
                <NumberField label="Night End (hour)" value={form.night_end} min={0} max={23}
                  onChange={v => update('night_end', v)} />
              </div>
              <SwitchField label="Weekend All Day" checked={form.weekend_all_day}
                onChange={v => update('weekend_all_day', v)} />
              <SwitchField label="Allow Weekday Day" checked={form.allow_weekday_day}
                onChange={v => update('allow_weekday_day', v)} />
            </>
          )}

          {section === 'appearance' && (
            <>
              <RadioGroupField label="Theme" value={form.theme}
                options={[
                  { value: 'dark', label: 'Dark' },
                  { value: 'light', label: 'Light' },
                ]}
                onChange={v => update('theme', v as 'dark' | 'light')} />
              <RadioGroupField label="Language" value={form.language}
                options={[
                  { value: 'zh', label: '中文' },
                  { value: 'en', label: 'English' },
                ]}
                onChange={v => update('language', v as 'zh' | 'en')} />
            </>
          )}

          {section === 'data' && (
            <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 6 }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>Data Directory</div>
              <code style={{ fontSize: 12, wordBreak: 'break-all' }}>{form.data_dir || '(not set)'}</code>
            </div>
          )}

          {section === 'about' && (
            <div style={{ padding: 16, background: 'var(--bg-secondary)', borderRadius: 6 }}>
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>LLM Router</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>v2.0.0</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Intelligent multi-model routing with predictive latency optimization.
                Built with Tauri + React + FastAPI.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---- Reusable field components (in-file to keep things simple) ---- */

function RadioGroupField({ label, value, options, onChange }: {
  label: string; value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6 }}>{label}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {options.map(opt => (
          <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer' }}>
            <input type="radio" name={label} value={opt.value} checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              style={{ accentColor: 'var(--accent)' }} />
            {opt.label}
          </label>
        ))}
      </div>
    </div>
  );
}

function SliderField({ label, value, min, max, step, onChange }: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 600 }}>{value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ width: '100%', accentColor: 'var(--accent)' }} />
    </div>
  );
}

function NumberField({ label, value, min, max, onChange }: {
  label: string; value: number; min?: number; max?: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</div>
      <input type="number" value={value} min={min} max={max}
        onChange={e => {
          const parsed = parseInt(e.target.value, 10);
          if (!isNaN(parsed)) onChange(parsed);
        }}
        style={{ height: 30, padding: '0 8px', borderRadius: 4, border: '1px solid var(--border)',
          background: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: 12, outline: 'none', width: '100%', boxSizing: 'border-box' }} />
    </div>
  );
}

function SwitchField({ label, checked, onChange }: {
  label: string; checked: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}>
      <span style={{ fontSize: 12 }}>{label}</span>
      <div
        onClick={() => onChange(!checked)}
        style={{
          width: 36, height: 20, borderRadius: 10, position: 'relative', cursor: 'pointer',
          background: checked ? 'var(--accent)' : 'var(--border)',
          transition: 'background 0.2s',
        }}
      >
        <div style={{
          position: 'absolute', top: 2, left: checked ? 18 : 2,
          width: 16, height: 16, borderRadius: '50%', background: '#fff',
          transition: 'left 0.2s',
        }} />
      </div>
    </label>
  );
}
