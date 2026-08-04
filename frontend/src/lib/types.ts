export interface ModelConfigOut {
  name: string;
  deployment: string;
  context_window: number;
  cost_input_1k: number;
  cost_output_1k: number;
  tags: string[];
}

export interface ProviderConfigOut {
  name: string;
  endpoint: string;
  status: string;
  models: ModelConfigOut[];
}

export interface ProbeResultOut {
  provider: string;
  model: string;
  success: boolean;
  latency_ms: number | null;
  error: string | null;
  timestamp: string;
}

export interface LatencyRecordOut {
  provider: string;
  model: string;
  latency_ms: number;
  timestamp: string;
  success: boolean;
}

export interface SettingsOut {
  strategy: string;
  latency_redline_ms: number;
  predictability_threshold: number;
  cycle_seconds: number;
  max_retries: number;
  night_start: number;
  night_end: number;
  weekend_all_day: boolean;
  allow_weekday_day: boolean;
  theme: string;
  language: string;
  data_dir: string;
}
