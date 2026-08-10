import { HashRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from '@/components/AppShell';
import { useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import ConfigPage from '@/pages/ConfigPage';
import DashboardPage from '@/pages/DashboardPage';
import TasksPage from '@/pages/TasksPage';
import LogsPage from '@/pages/LogsPage';
import SettingsPage from '@/pages/SettingsPage';

function ThemeInit() {
  const theme = useAppStore((s) => s.theme);
  useEffect(() => {
    document.documentElement.className = theme === 'dark' ? 'dark' : '';
  }, [theme]);
  return null;
}

export default function App() {
  return (
    <HashRouter>
      <ThemeInit />
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="config" element={<ConfigPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
