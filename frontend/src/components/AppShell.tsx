import { Outlet } from 'react-router-dom';
import { NavBar } from './NavBar';

export function AppShell() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <NavBar />
      <main style={{ flex: 1, overflow: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
