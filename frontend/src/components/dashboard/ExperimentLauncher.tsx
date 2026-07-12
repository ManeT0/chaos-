import { useState } from 'react';
import { Play, Activity, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function ExperimentLauncher() {
  const [running, setRunning] = useState(false);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 700, margin: 0 }}>Dashboard</h1>
          <p style={{ color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>Monitor SLOs and launch experiments</p>
        </div>
        <button 
          className="btn btn-primary"
          onClick={() => setRunning(!running)}
        >
          {running ? <Activity size={18} className="animate-pulse" /> : <Play size={18} />}
          {running ? 'Halt All Chaos' : 'Launch New Experiment'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
        <div className="glass-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ color: 'var(--color-success)' }}><CheckCircle2 size={24} /></div>
            <h3 style={{ margin: 0 }}>SLO Budget</h3>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, margin: '1rem 0' }}>98.5%</div>
          <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--color-bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: '85%', height: '100%', backgroundColor: 'var(--color-success)' }}></div>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', marginTop: '0.5rem' }}>45m error budget remaining</p>
        </div>

        <div className="glass-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ color: 'var(--color-warning)' }}><Activity size={24} /></div>
            <h3 style={{ margin: 0 }}>Active Experiments</h3>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, margin: '1rem 0' }}>{running ? '1' : '0'}</div>
          {running ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-warning)', fontSize: '0.875rem' }}>
              <Activity size={14} className="animate-pulse" /> Running: Pod Kill (frontend)
            </div>
          ) : (
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>System is in steady state</p>
          )}
        </div>

        <div className="glass-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ color: 'var(--color-info)' }}><ShieldAlert size={24} /></div>
            <h3 style={{ margin: 0 }}>Recent Executions</h3>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, margin: '1rem 0' }}>24</div>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>Last 7 days. 22 passed, 2 rolled back.</p>
        </div>
      </div>
      
      {/* Example Metrics Area */}
      <div className="glass-card" style={{ minHeight: '300px' }}>
        <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Activity size={20} color="var(--color-accent-primary)" /> Live System Metrics
        </h3>
        <div style={{ 
          height: '220px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          border: '1px dashed var(--color-border)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--color-text-muted)'
        }}>
          Recharts metrics chart would render here via WebSocket...
        </div>
      </div>
    </div>
  );
}
