// TopBar.jsx — Tiered Sync Tablet UI Kit
// Persistent top bar: sync status, node identity, role badge, nav

const topBarStyles = {
  bar: {
    background: '#1c2030',
    borderBottom: '1px solid #2e3650',
    padding: '0 16px',
    height: 52,
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    flexShrink: 0,
    userSelect: 'none',
  },
  nodeId: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 13,
    fontWeight: 600,
    color: '#f0f2f7',
    letterSpacing: '0.02em',
  },
  sep: { color: '#2e3650', fontSize: 18, fontWeight: 300 },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 5,
    padding: '2px 9px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.04em',
  },
  dot: { width: 6, height: 6, borderRadius: '50%' },
  spacer: { flex: 1 },
  syncLabel: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
    color: '#4a5168',
  },
  navBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '6px 10px',
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 500,
    color: '#8a94b0',
    transition: 'all 150ms ease-in-out',
    fontFamily: "'IBM Plex Sans', sans-serif",
  },
  navBtnActive: {
    background: '#252b3b',
    color: '#f0f2f7',
  },
};

const ROLE_STYLES = {
  COMMAND: { background: 'rgba(245,104,30,0.15)', color: '#f5681e', border: '1px solid rgba(245,104,30,0.4)', dot: '#f5681e' },
  RESPONDER: { background: 'rgba(34,120,212,0.12)', color: '#6aaef0', border: '1px solid rgba(34,120,212,0.3)', dot: '#2278d4' },
  TABLET: { background: 'rgba(74,81,104,0.2)', color: '#8a94b0', border: '1px solid #2e3650', dot: '#4a5168' },
};

const SYNC_STYLES = {
  LIVE:    { background: 'rgba(45,182,125,0.12)', color: '#52d09a', border: '1px solid rgba(45,182,125,0.3)', dot: '#2db67d' },
  SYNCING: { background: 'rgba(245,178,30,0.1)',  color: '#fac84e', border: '1px solid rgba(245,178,30,0.3)',  dot: '#f5b21e' },
  OFFLINE: { background: 'rgba(232,48,42,0.1)',   color: '#ef5f5a', border: '1px solid rgba(232,48,42,0.3)',  dot: '#e8302a' },
};

function TopBar({ nodeId, role, syncStatus, screen, setScreen }) {
  const roleSt = ROLE_STYLES[role] || ROLE_STYLES.TABLET;
  const syncSt = SYNC_STYLES[syncStatus] || SYNC_STYLES.OFFLINE;
  const navItems = [
    { id: 'incident', label: 'Incident' },
    { id: 'fleet',    label: 'Fleet' },
    { id: 'siteplan', label: 'Site Plan' },
    { id: 'outbox',   label: 'Outbox' },
  ];
  return (
    <div style={topBarStyles.bar}>
      <span style={topBarStyles.nodeId}>{nodeId}</span>
      <span style={topBarStyles.sep}>|</span>
      <span style={{ ...topBarStyles.badge, ...roleSt }}>
        <span style={{ ...topBarStyles.dot, background: roleSt.dot }} />
        {role}
      </span>
      <span style={{ ...topBarStyles.badge, ...syncSt }}>
        <span style={{ ...topBarStyles.dot, background: syncSt.dot,
          animation: syncStatus === 'SYNCING' ? 'tbPulse 1s infinite' : 'none' }} />
        {syncStatus}
      </span>
      <span style={topBarStyles.spacer} />
      {navItems.map(n => (
        <button
          key={n.id}
          style={{ ...topBarStyles.navBtn, ...(screen === n.id ? topBarStyles.navBtnActive : {}) }}
          onClick={() => setScreen(n.id)}
        >{n.label}</button>
      ))}
    </div>
  );
}

Object.assign(window, { TopBar });
