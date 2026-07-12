import { NavLink } from 'react-router-dom';
import { Activity, Target, Settings, ShieldAlert, BarChart2 } from 'lucide-react';

export default function Sidebar() {
  const links = [
    { to: '/dashboard', label: 'Dashboard', icon: <Activity size={20} /> },
    { to: '/targets', label: 'Targets', icon: <Target size={20} /> },
    { to: '/experiments', label: 'Experiments', icon: <ShieldAlert size={20} /> },
    { to: '/reports', label: 'Reports', icon: <BarChart2 size={20} /> },
    { to: '/settings', label: 'Settings', icon: <Settings size={20} /> },
  ];

  return (
    <aside style={{
      width: '260px',
      backgroundColor: 'var(--color-bg-secondary)',
      borderRight: '1px solid var(--color-border)',
      display: 'flex',
      flexDirection: 'column',
      padding: '1.5rem 0'
    }}>
      <div style={{ padding: '0 1.5rem', marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '8px',
          background: 'linear-gradient(135deg, var(--color-accent-primary), var(--color-accent-secondary))',
          display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white'
        }}>
          <Activity size={18} />
        </div>
        <h2 style={{ fontSize: '1.125rem', margin: 0, fontWeight: 700 }}>Chaos Platform</h2>
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '0 1rem' }}>
        {links.map(link => (
          <NavLink
            key={link.to}
            to={link.to}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: '0.75rem',
              padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)',
              color: isActive ? 'white' : 'var(--color-text-secondary)',
              backgroundColor: isActive ? 'rgba(79, 70, 229, 0.15)' : 'transparent',
              fontWeight: isActive ? 600 : 500,
              textDecoration: 'none',
              transition: 'all 0.2s ease',
              border: isActive ? '1px solid rgba(79, 70, 229, 0.3)' : '1px solid transparent'
            })}
          >
            {link.icon}
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
