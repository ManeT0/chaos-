import { Target, Plus, Trash2 } from 'lucide-react';

export default function TargetManager() {
  const targets = [
    { id: '1', name: 'Frontend K8s Pods', type: 'kubernetes_pod', scope: 'namespace: default' },
    { id: '2', name: 'User DB Primary', type: 'database', scope: 'host: db.internal' },
    { id: '3', name: 'Payment API', type: 'http_endpoint', scope: 'url: /api/pay' }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, margin: 0 }}>Target Manager</h1>
          <p style={{ color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>Configure blast radius and targets</p>
        </div>
        <button className="btn btn-primary">
          <Plus size={18} />
          Add Target
        </button>
      </div>

      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ backgroundColor: 'rgba(0,0,0,0.2)', borderBottom: '1px solid var(--color-border)' }}>
              <th style={{ padding: '1rem', fontWeight: 600 }}>Name</th>
              <th style={{ padding: '1rem', fontWeight: 600 }}>Type</th>
              <th style={{ padding: '1rem', fontWeight: 600 }}>Scope</th>
              <th style={{ padding: '1rem', fontWeight: 600, textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {targets.map((t, idx) => (
              <tr key={t.id} style={{ borderBottom: idx !== targets.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
                <td style={{ padding: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Target size={16} color="var(--color-accent-primary)" />
                    {t.name}
                  </div>
                </td>
                <td style={{ padding: '1rem' }}><span style={{ 
                  backgroundColor: 'var(--color-bg-tertiary)', 
                  padding: '0.25rem 0.5rem', 
                  borderRadius: '4px',
                  fontSize: '0.875rem'
                }}>{t.type}</span></td>
                <td style={{ padding: '1rem', color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>{t.scope}</td>
                <td style={{ padding: '1rem', textAlign: 'right' }}>
                  <button className="btn btn-danger" style={{ padding: '0.5rem' }}>
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
