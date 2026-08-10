import { Outlet } from 'react-router-dom';
import { NavBar } from './NavBar';
import { useEffect } from 'react';

export function AppShell() {
  // Workaround for WebView2 issue: after window resize (especially
  // restore from maximized), the scroll container caches stale
  // scrollHeight. Force a layout recalculation on every resize.
  useEffect(() => {
    const el = document.documentElement;
    const forceLayout = () => {
      // Reading offsetHeight forces synchronous layout recalculation.
      // eslint-disable-next-line @typescript-eslint/no-unused-expressions
      el.offsetHeight;
    };
    window.addEventListener('resize', forceLayout);
    return () => window.removeEventListener('resize', forceLayout);
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <NavBar />
      <main style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
