import { create } from 'zustand';
import type { ProviderConfigOut, LatencyRecordOut, SettingsOut } from '@/lib/types';

interface AppState {
  // Theme
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  setTheme: (t: 'dark' | 'light') => void;

  // Providers
  providers: ProviderConfigOut[];
  setProviders: (p: ProviderConfigOut[]) => void;
  activeProvider: string | null;
  setActiveProvider: (name: string | null) => void;

  // Selected models for dashboard
  selectedModels: Record<string, string[]>;
  toggleModel: (provider: string, model: string) => void;
  setSelectedModels: (sm: Record<string, string[]>) => void;

  // Latency cache
  latencyCache: LatencyRecordOut[];
  setLatencyCache: (records: LatencyRecordOut[]) => void;
  appendLatency: (records: LatencyRecordOut[]) => void;

  // Settings
  settings: SettingsOut;
  setSettings: (s: SettingsOut) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Theme -- init from localStorage
  theme: (localStorage.getItem('llm-router-theme') as 'dark' | 'light') || 'dark',
  toggleTheme: () =>
    set((s) => {
      const next = s.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('llm-router-theme', next);
      document.documentElement.className = next;
      return { theme: next };
    }),
  setTheme: (t) => {
    localStorage.setItem('llm-router-theme', t);
    document.documentElement.className = t;
    set({ theme: t });
  },

  // Providers
  providers: [],
  setProviders: (providers) => set({ providers }),
  activeProvider: null,
  setActiveProvider: (name) => set({ activeProvider: name }),

  // Selected models
  selectedModels: {},
  toggleModel: (provider, model) =>
    set((s) => {
      const current = s.selectedModels[provider] || [];
      const next = current.includes(model)
        ? current.filter((m) => m !== model)
        : [...current, model];
      return {
        selectedModels: {
          ...s.selectedModels,
          [provider]: next,
        },
      };
    }),
  setSelectedModels: (sm) => set({ selectedModels: sm }),

  // Latency cache
  latencyCache: [],
  setLatencyCache: (records) => set({ latencyCache: records }),
  appendLatency: (records) =>
    set((s) => {
      const merged = [...s.latencyCache, ...records];
      // Keep last 600 entries
      return { latencyCache: merged.slice(-600) };
    }),

  // Settings
  settings: {
    strategy: 'baseline',
    latency_redline_ms: 5000,
    predictability_threshold: 0.3,
    cycle_seconds: 30,
    max_retries: 3,
    night_start: 22,
    night_end: 6,
    weekend_all_day: true,
    allow_weekday_day: false,
    theme: 'dark',
    language: 'zh',
    data_dir: '',
  },
  setSettings: (settings) => set({ settings }),
}));
