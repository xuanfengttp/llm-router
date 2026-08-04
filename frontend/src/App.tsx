import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from '@/components/AppShell';
import { useEffect } from 'react';
import { useAppStore } from '@/store/appStore';

function ThemeInit() {
  const theme = useAppStore((s) => s.theme);
  useEffect(() => {
    document.documentElement.className = theme;
  }, [theme]);
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeInit />
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<PlaceholderPage title="Dashboard" />} />
          <Route path="config" element={<PlaceholderPage title="Config" />} />
          <Route path="tasks" element={<PlaceholderPage title="Tasks" />} />
          <Route path="logs" element={<PlaceholderPage title="Logs" />} />
          <Route path="settings" element={<PlaceholderPage title="Settings" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      color: 'var(--text-secondary)',
      fontSize: 18,
    }}>
      {title} -- coming soon
    </div>
  );
}
