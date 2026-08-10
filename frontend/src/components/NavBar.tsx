import { NavLink } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';
import { LayoutDashboard, Settings2, ListTodo, ScrollText, SlidersHorizontal } from 'lucide-react';
import { useT } from '@/locales';

export function NavBar() {
  const t = useT();
  const NAV_ITEMS = [
    { to: '/', icon: LayoutDashboard, label: t('控制台') },
    { to: '/config', icon: Settings2, label: t('配置') },
    { to: '/tasks', icon: ListTodo, label: t('任务') },
    { to: '/logs', icon: ScrollText, label: t('日志') },
    { to: '/settings', icon: SlidersHorizontal, label: t('设置') },
  ];

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
