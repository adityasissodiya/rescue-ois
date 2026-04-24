// FleetView.jsx — Vehicle and tablet fleet status

const fleetStyles = {
  root: { flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 10 },
  sectionLabel: { fontSize: 10, fontWeight: 600, color: '#4a5168', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4, marginTop: 4 },
  nodeCard: { background: '#252b3b', border: '1px solid #2e3650', borderRadius: 8, padding: '12px 14px', display: 'flex', alignItems: 'flex-start', gap: 12 },
  iconBox: { width: 36, height: 36, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  nodeId: { fontSize: 14, fontWeight: 700, color: '#f0f2f7', fontFamily: "'JetBrains Mono', monospace" },
  nodeSub: { fontSize: 12, color: '#8a94b0', marginTop: 1 },
  badge: { display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 600 },
  dot: { width: 5, height: 5, borderRadius: '50%' },
  metaRow: { display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' },
  chip: { background: '#1c2030', border: '1px solid #2e3650', borderRadius: 4, padding: '2px 7px', fontSize: 10, color: '#8a94b0', fontFamily: "'JetBrains Mono', monospace" },
  right: { marginLeft: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 },
  syncTime: { fontSize: 10, color: '#4a5168', fontFamily: "'JetBrains Mono', monospace" },
};

const VEHICLES = [
  { id: 'CMD-01', sub: 'Command vehicle · Tier 2', role: 'COMMAND', sync: 'LIVE', outbox: 0, wlan: 'WAN+mesh', last: '14:45:02', color: '#f5681e', bg: 'rgba(245,104,30,0.12)' },
  { id: 'RSP-03', sub: 'Responder vehicle · Tier 2', role: 'RESPONDER', sync: 'LIVE', outbox: 3, wlan: 'mesh', last: '14:43:17', color: '#2278d4', bg: 'rgba(0,87,168,0.12)' },
  { id: 'RSP-07', sub: 'Responder vehicle · Tier 2', role: 'RESPONDER', sync: 'OFFLINE', outbox: 0, wlan: 'WAN partition', last: '13:54:02', color: '#e8302a', bg: 'rgba(232,48,42,0.1)' },
];

const TABLETS = [
  { id: 'TAB-A', parent: 'CMD-01', sync: 'LIVE', outbox: 0, last: '14:44:58' },
  { id: 'TAB-B', parent: 'RSP-03', sync: 'SYNCING', outbox: 2, last: '14:43:00' },
  { id: 'TAB-C', parent: 'RSP-03', sync: 'LIVE', outbox: 0, last: '14:44:10' },
  { id: 'TAB-D', parent: 'RSP-07', sync: 'OFFLINE', outbox: 5, last: '13:54:00' },
];

const SYNC_BADGE = {
  LIVE:    { bg: 'rgba(45,182,125,0.12)', color: '#52d09a', border: '1px solid rgba(45,182,125,0.3)', dot: '#2db67d' },
  SYNCING: { bg: 'rgba(245,178,30,0.1)',  color: '#fac84e', border: '1px solid rgba(245,178,30,0.3)', dot: '#f5b21e' },
  OFFLINE: { bg: 'rgba(232,48,42,0.1)',   color: '#ef5f5a', border: '1px solid rgba(232,48,42,0.3)', dot: '#e8302a' },
};

function FleetView({ onPromote }) {
  return (
    <div style={fleetStyles.root}>
      <div style={fleetStyles.sectionLabel}>Vehicle Edge Nodes — Tier 2</div>
      {VEHICLES.map(v => {
        const sb = SYNC_BADGE[v.sync];
        return (
          <div key={v.id} style={{ ...fleetStyles.nodeCard, borderTop: v.role === 'COMMAND' ? `2px solid ${v.color}` : undefined }}>
            <div style={{ ...fleetStyles.iconBox, background: v.bg }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={v.color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="1" y="3" width="15" height="13" rx="1"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <div style={fleetStyles.nodeId}>{v.id}</div>
              <div style={fleetStyles.nodeSub}>{v.sub}</div>
              <div style={fleetStyles.metaRow}>
                <span style={{ ...fleetStyles.badge, background: sb.bg, color: sb.color, border: sb.border }}>
                  <span style={{ ...fleetStyles.dot, background: sb.dot }} />{v.sync}
                </span>
                <span style={fleetStyles.chip}>{v.wlan}</span>
                {v.outbox > 0 && <span style={{ ...fleetStyles.chip, color: '#fac84e', borderColor: 'rgba(245,178,30,0.3)' }}>outbox: {v.outbox}</span>}
              </div>
            </div>
            <div style={fleetStyles.right}>
              <div style={fleetStyles.syncTime}>{v.last}</div>
              {v.role === 'RESPONDER' && v.sync !== 'OFFLINE' && (
                <button onClick={onPromote} style={{ background: 'none', border: '1px solid #2e3650', borderRadius: 5, color: '#8a94b0', fontSize: 11, fontWeight: 500, padding: '3px 8px', cursor: 'pointer', fontFamily: "'IBM Plex Sans', sans-serif" }}>
                  Promote
                </button>
              )}
            </div>
          </div>
        );
      })}

      <div style={{ ...fleetStyles.sectionLabel, marginTop: 8 }}>Field Tablets — Tier 3</div>
      {TABLETS.map(t => {
        const sb = SYNC_BADGE[t.sync];
        return (
          <div key={t.id} style={fleetStyles.nodeCard}>
            <div style={{ ...fleetStyles.iconBox, background: '#1c2030' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4a5168" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ ...fleetStyles.nodeId, fontSize: 13 }}>{t.id}</div>
              <div style={fleetStyles.nodeSub}>via {t.parent}</div>
              <div style={fleetStyles.metaRow}>
                <span style={{ ...fleetStyles.badge, background: sb.bg, color: sb.color, border: sb.border }}>
                  <span style={{ ...fleetStyles.dot, background: sb.dot }} />{t.sync}
                </span>
                {t.outbox > 0 && <span style={{ ...fleetStyles.chip, color: '#fac84e' }}>outbox: {t.outbox}</span>}
              </div>
            </div>
            <div style={fleetStyles.syncTime}>{t.last}</div>
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, { FleetView });
