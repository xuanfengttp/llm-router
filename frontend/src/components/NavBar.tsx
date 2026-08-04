import { NavLink } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';
import { LayoutDashboard, Settings2, ListTodo, ScrollText, SlidersHorizontal } from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/config', icon: Settings2, label: 'Config' },
  { to: '/tasks', icon: ListTodo, label: 'Tasks' },
  { to: '/logs', icon: ScrollText, label: 'Logs' },
  { to: '/settings', icon: SlidersHorizontal, label: 'Settings' },
];

export function NavBar() {
  return (
    <nav
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: 40,
        padding: '0 8px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border)',
        userSelect: 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--accent)', marginRight: 16, marginLeft: 8 }}>
          LLM Router
        </span>
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '4px 12px',
              borderRadius: 4,
              fontSize: 12,
              textDecoration: 'none',
              color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
              background: isActive ? 'var(--bg-hover)' : 'transparent',
            })}
          >
            <Icon size={14} />
            {label}
          </NavLink>
        ))}
      </div>
      <ThemeToggle />
    </nav>
  );
}
