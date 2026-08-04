import type { ProviderConfigOut, ProbeResultOut, LatencyRecordOut, SettingsOut, TaskOut } from '@/lib/types';

const BASE = '';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE + url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  // Providers
  listProviders: () => fetchJSON<ProviderConfigOut[]>('/api/providers'),
  createProvider: (body: { name: string; endpoint: string; api_key?: string }) =>
    fetchJSON<ProviderConfigOut>('/api/providers', { method: 'POST', body: JSON.stringify(body) }),
  deleteProvider: (name: string) =>
    fetch('/api/providers/' + encodeURIComponent(name), { method: 'DELETE' }),
  updateApiKey: (name: string, api_key: string) =>
    fetchJSON<ProviderConfigOut>('/api/providers/' + encodeURIComponent(name) + '/api-key', {
      method: 'PUT', body: JSON.stringify({ api_key }),
    }),
  addModel: (name: string, body: { name: string; deployment?: string; context_window?: number; cost_input_1k?: number; cost_output_1k?: number }) =>
    fetchJSON<ProviderConfigOut>('/api/providers/' + encodeURIComponent(name) + '/models', {
      method: 'POST', body: JSON.stringify(body),
    }),
  removeModel: (pname: string, mname: string) =>
    fetchJSON<ProviderConfigOut>('/api/providers/' + encodeURIComponent(pname) + '/models/' + encodeURIComponent(mname), {
      method: 'DELETE',
    }),

  // Dashboard
  getStatus: () =>
    fetchJSON<{ providers: ProviderConfigOut[]; selected_models: Record<string, string[]> }>('/api/dashboard/status'),
  probe: (providers: string[], models: string[]) =>
    fetchJSON<ProbeResultOut[]>('/api/dashboard/probe', {
      method: 'POST', body: JSON.stringify({ providers, models }),
    }),
  getLatency: (provider: string, model: string, limit?: number) =>
    fetchJSON<LatencyRecordOut[]>(
      `/api/dashboard/latency?provider=${encodeURIComponent(provider)}&model=${encodeURIComponent(model)}&limit=${limit ?? 300}`
    ),

  // Tasks
  listTasks: (limit?: number, offset?: number) =>
    fetchJSON<TaskOut[]>(`/api/tasks?limit=${limit ?? 50}&offset=${offset ?? 0}`),
  createTask: (body: { prompt: string; target_model?: string }) =>
    fetchJSON<TaskOut>('/api/tasks', { method: 'POST', body: JSON.stringify(body) }),
  cancelTask: (id: string) =>
    fetchJSON<TaskOut>('/api/tasks/' + id + '/cancel', { method: 'POST' }),
  retryTask: (id: string) =>
    fetchJSON<TaskOut>('/api/tasks/' + id + '/retry', { method: 'POST' }),

  // Settings
  getSettings: () => fetchJSON<SettingsOut>('/api/settings'),
  updateSettings: (body: Partial<SettingsOut>) =>
    fetchJSON<SettingsOut>('/api/settings', { method: 'PUT', body: JSON.stringify(body) }),
};
