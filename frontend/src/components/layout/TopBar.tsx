import { Bell, User } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';

export default function TopBar() {
  const { user, logout } = useAuthStore();

  return (
    <header style={{
      height: '64px',
      backgroundColor: 'var(--color-bg-primary)',
      borderBottom: '1px solid var(--color-border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'flex-end',
      padding: '0 2rem',
      gap: '1.5rem'
    }}>
      <div style={{ position: 'relative', cursor: 'pointer', color: 'var(--color-text-secondary)' }}>
        <Bell size={20} />
        <span style={{
          position: 'absolute', top: '-4px', right: '-4px',
          width: '8px', height: '8px', borderRadius: '50%',
          backgroundColor: 'var(--color-error)'
        }}></span>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{user?.name || 'Operator'}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{user?.role || 'Admin'}</div>
        </div>
        <div style={{
          width: '36px', height: '36px', borderRadius: '50%',
          backgroundColor: 'var(--color-bg-tertiary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer'
        }} onClick={logout}>
          <User size={18} />
        </div>
      </div>
    </header>
  );
}
