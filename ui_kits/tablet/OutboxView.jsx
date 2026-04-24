// OutboxView.jsx — Queued field edits waiting to forward to command

const outboxStyles = {
  root: { flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 10 },
  header: { background: '#252b3b', border: '1px solid #2e3650', borderRadius: 8, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 10 },
  headerText: { flex: 1 },
  headerTitle: { fontSize: 15, fontWeight: 600, color: '#f0f2f7' },
  headerSub: { fontSize: 12, color: '#8a94b0', marginTop: 2 },
  sendBtn: { background: '#f5681e', color: '#fff', border: 'none', cursor: 'pointer', fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 600, borderRadius: 6, height: 44, padding: '0 18px', fontSize: 13 },
  sendBtnDisabled: { background: '#1c2030', color: '#4a5168', border: '1px solid #2e3650', cursor: 'not-allowed' },
  emptyState: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, padding: 40 },
  emptyIcon: { opacity: 0.3 },
  emptyText: { fontSize: 14, color: '#4a5168', textAlign: 'center' },
  editCard: { background: '#252b3b', border: '1px solid #2e3650', borderRadius: 8, padding: '11px 14px', display: 'flex', gap: 10, alignItems: 'flex-start' },
  editSeq: { fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#4a5168', width: 24, paddingTop: 2 },
  editBody: { flex: 1 },
  editTitle: { fontSize: 13, fontWeight: 600, color: '#f0f2f7', marginBottom: 2 },
  editDetail: { fontSize: 12, color: '#8a94b0', lineHeight: 1.4 },
  editMeta: { fontSize: 10, fontFamily: "'JetBrains Mono', monospace", color: '#4a5168', marginTop: 4 },
  queuedBadge: { background: 'rgba(0,87,168,0.12)', color: '#6aaef0', border: '1px solid rgba(0,87,168,0.3)', borderRadius: 4, fontSize: 10, fontWeight: 600, padding: '2px 7px', flexShrink: 0 },
};

const EDITS = [
  { seq: 1, title: 'Hazard note added', detail: 'Basement fuel storage, NE corner — diesel 2000L', time: '14:41:02', author: 'TAB-B' },
  { seq: 2, title: 'Status update', detail: 'Sector B cleared. No casualties found, floor 1 W.', time: '14:42:18', author: 'TAB-C' },
  { seq: 3, title: 'Resource request', detail: 'Additional breathing apparatus needed at entry point S.', time: '14:44:05', author: 'TAB-B' },
];

function OutboxView({ connected }) {
  const [edits, setEdits] = React.useState(connected ? [] : EDITS);
  const [sending, setSending] = React.useState(false);

  function handleSend() {
    if (!edits.length || sending) return;
    setSending(true);
    setTimeout(() => { setEdits([]); setSending(false); }, 1200);
  }

  return (
    <div style={outboxStyles.root}>
      <div style={outboxStyles.header}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={edits.length ? '#f5b21e' : '#2db67d'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
        <div style={outboxStyles.headerText}>
          <div style={outboxStyles.headerTitle}>Outbox — {edits.length} edit{edits.length !== 1 ? 's' : ''} queued</div>
          <div style={outboxStyles.headerSub}>{edits.length ? 'Pending forward to CMD-01' : 'All edits forwarded and committed'}</div>
        </div>
        <button
          style={{ ...outboxStyles.sendBtn, ...(edits.length === 0 ? outboxStyles.sendBtnDisabled : {}) }}
          onClick={handleSend}
          disabled={!edits.length || sending}
        >{sending ? 'Forwarding…' : 'Forward All'}</button>
      </div>

      {edits.length === 0 ? (
        <div style={outboxStyles.emptyState}>
          <svg style={outboxStyles.emptyIcon} width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2db67d" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <div style={outboxStyles.emptyText}>Outbox is empty.<br/>All edits committed to incident journal.</div>
        </div>
      ) : (
        edits.map((e, i) => (
          <div key={i} style={outboxStyles.editCard}>
            <div style={outboxStyles.editSeq}>#{e.seq}</div>
            <div style={outboxStyles.editBody}>
              <div style={outboxStyles.editTitle}>{e.title}</div>
              <div style={outboxStyles.editDetail}>{e.detail}</div>
              <div style={outboxStyles.editMeta}>{e.time} · {e.author}</div>
            </div>
            <div style={outboxStyles.queuedBadge}>QUEUED</div>
          </div>
        ))
      )}
    </div>
  );
}

Object.assign(window, { OutboxView });
