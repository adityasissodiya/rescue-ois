// IncidentView.jsx — Active incident overview screen

const incidentStyles = {
  root: { flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 },
  row: { display: 'flex', gap: 12 },
  card: { background: '#252b3b', border: '1px solid #2e3650', borderRadius: 8, padding: '12px 14px' },
  cardTitle: { fontSize: 11, fontWeight: 600, color: '#4a5168', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 },
  incidentName: { fontSize: 20, fontWeight: 700, color: '#f0f2f7', marginBottom: 4 },
  incidentSub: { fontSize: 13, color: '#8a94b0', marginBottom: 10 },
  metaRow: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 },
  chip: { background: '#1c2030', border: '1px solid #2e3650', borderRadius: 4, padding: '3px 8px', fontSize: 11, color: '#8a94b0', fontFamily: "'JetBrains Mono', monospace" },
  seqNum: { fontFamily: "'JetBrains Mono', monospace", fontSize: 22, fontWeight: 700, color: '#2db67d' },
  seqLabel: { fontSize: 11, color: '#4a5168', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: 2 },
  statGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, flex: 1 },
  stat: { background: '#1c2030', border: '1px solid #2e3650', borderRadius: 6, padding: '10px 12px', textAlign: 'center' },
  statVal: { fontSize: 20, fontWeight: 700, color: '#f0f2f7', fontFamily: "'JetBrains Mono', monospace" },
  statKey: { fontSize: 10, color: '#4a5168', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: 2 },
  mapPlaceholder: { background: '#141820', border: '1px solid #2e3650', borderRadius: 8, height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 8 },
  mapLabel: { fontSize: 12, color: '#2e3650', fontFamily: "'JetBrains Mono', monospace" },
  journalItem: { padding: '8px 0', borderBottom: '1px solid #1c2030', display: 'flex', gap: 10 },
  journalTime: { fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: '#4a5168', width: 52, flexShrink: 0, paddingTop: 2 },
  journalText: { fontSize: 13, color: '#f0f2f7', lineHeight: 1.4 },
  journalAuthor: { fontSize: 11, color: '#8a94b0', marginTop: 2 },
  btn: { border: 'none', cursor: 'pointer', fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 600, borderRadius: 6, height: 44, padding: '0 18px', fontSize: 13, transition: 'all 150ms ease-in-out' },
};

const JOURNAL = [
  { time: '14:32', text: 'Incident journal opened. Bootstrap complete.', author: 'cmd-01 · auto' },
  { time: '14:34', text: 'RSP-03 joined mesh. Site plan synchronised.', author: 'cmd-01' },
  { time: '14:37', text: 'RSP-07 WAN partition detected. Mesh-only mode.', author: 'system' },
  { time: '14:41', text: 'Hazard note added: basement fuel storage, NE corner.', author: 'TAB-B · rsp-03' },
  { time: '14:45', text: 'RSP-07 outbox forwarded (11 edits). Sequence reconciled.', author: 'cmd-01' },
];

function IncidentView({ onOpenOutbox }) {
  return (
    <div style={incidentStyles.root}>
      {/* Incident header */}
      <div style={{ ...incidentStyles.card, borderTop: '2px solid #f5681e' }}>
        <div style={incidentStyles.cardTitle}>Active Incident</div>
        <div style={incidentStyles.incidentName}>Brand fire — Industrivägen 14</div>
        <div style={incidentStyles.incidentSub}>Gothenburg · Alarm 14:30 · Ongoing</div>
        <div style={incidentStyles.metaRow}>
          <span style={incidentStyles.chip}>INC-2026-0412</span>
          <span style={incidentStyles.chip}>cmd-01 · COMMAND</span>
          <span style={incidentStyles.chip}>WAN: up</span>
          <span style={incidentStyles.chip}>mesh: 3 nodes</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={{ ...incidentStyles.btn, background: '#f5681e', color: '#fff' }}>Commit Event</button>
          <button style={{ ...incidentStyles.btn, background: '#252b3b', color: '#f0f2f7', border: '1px solid #2e3650' }} onClick={onOpenOutbox}>View Outbox (0)</button>
        </div>
      </div>

      <div style={incidentStyles.row}>
        {/* Sequence counter */}
        <div style={{ ...incidentStyles.card, width: 140, flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div style={incidentStyles.seqNum}>00247</div>
          <div style={incidentStyles.seqLabel}>Seq #</div>
        </div>
        {/* Stats */}
        <div style={{ ...incidentStyles.statGrid, flex: 1 }}>
          <div style={incidentStyles.stat}><div style={incidentStyles.statVal}>3</div><div style={incidentStyles.statKey}>Vehicles</div></div>
          <div style={incidentStyles.stat}><div style={incidentStyles.statVal}>7</div><div style={incidentStyles.statKey}>Tablets</div></div>
          <div style={{ ...incidentStyles.stat, borderColor: 'rgba(45,182,125,0.3)' }}><div style={{ ...incidentStyles.statVal, color: '#2db67d' }}>0</div><div style={incidentStyles.statKey}>Queued edits</div></div>
          <div style={incidentStyles.stat}><div style={{ ...incidentStyles.statVal, fontSize: 15 }}>38 ms</div><div style={incidentStyles.statKey}>Sync latency</div></div>
        </div>
      </div>

      {/* Map placeholder */}
      <div style={incidentStyles.mapPlaceholder}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2e3650" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
        </svg>
        <div style={incidentStyles.mapLabel}>MapLibre · dark vector tile cache</div>
        <div style={{ fontSize: 10, color: '#2e3650', fontFamily: "'JetBrains Mono', monospace" }}>57.7°N 11.97°E · zoom 16</div>
      </div>

      {/* Journal */}
      <div style={incidentStyles.card}>
        <div style={incidentStyles.cardTitle}>Incident journal</div>
        {JOURNAL.map((e, i) => (
          <div key={i} style={{ ...incidentStyles.journalItem, borderBottom: i === JOURNAL.length - 1 ? 'none' : undefined }}>
            <div style={incidentStyles.journalTime}>{e.time}</div>
            <div>
              <div style={incidentStyles.journalText}>{e.text}</div>
              <div style={incidentStyles.journalAuthor}>{e.author}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { IncidentView });
