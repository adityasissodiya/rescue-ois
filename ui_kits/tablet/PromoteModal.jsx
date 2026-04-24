// PromoteModal.jsx — Command promotion confirmation modal

const promoteModalStyles = {
  overlay: { position: 'fixed', inset: 0, background: 'rgba(15,17,23,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, backdropFilter: 'blur(3px)' },
  modal: { background: '#1c2030', border: '1px solid #2e3650', borderRadius: 12, padding: 24, width: 360, boxShadow: '0 8px 32px rgba(0,0,0,0.65)' },
  topBorder: { height: 3, background: '#f5681e', borderRadius: '12px 12px 0 0', margin: '-24px -24px 20px' },
  icon: { width: 44, height: 44, background: 'rgba(245,104,30,0.12)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 },
  title: { fontSize: 17, fontWeight: 700, color: '#f0f2f7', marginBottom: 6 },
  body: { fontSize: 13, color: '#8a94b0', lineHeight: 1.55, marginBottom: 16 },
  warningBox: { background: 'rgba(232,48,42,0.08)', border: '1px solid rgba(232,48,42,0.25)', borderRadius: 6, padding: '10px 12px', marginBottom: 18 },
  warningText: { fontSize: 12, color: '#ef5f5a', lineHeight: 1.5 },
  nodeRow: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 16, background: '#252b3b', border: '1px solid #2e3650', borderRadius: 6, padding: '10px 12px' },
  nodeId: { fontFamily: "'JetBrains Mono', monospace", fontSize: 14, fontWeight: 700, color: '#f0f2f7', flex: 1 },
  nodeSub: { fontSize: 11, color: '#8a94b0' },
  btnRow: { display: 'flex', gap: 8 },
  btnCancel: { flex: 1, background: 'transparent', border: '1px solid #2e3650', color: '#8a94b0', fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 600, fontSize: 13, height: 44, borderRadius: 6, cursor: 'pointer' },
  btnConfirm: { flex: 2, background: '#f5681e', color: '#fff', border: 'none', fontFamily: "'IBM Plex Sans', sans-serif", fontWeight: 700, fontSize: 13, height: 44, borderRadius: 6, cursor: 'pointer' },
  successState: { display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '8px 0 4px' },
  successIcon: { width: 48, height: 48, background: 'rgba(245,104,30,0.12)', borderRadius: 999, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  successTitle: { fontSize: 16, fontWeight: 700, color: '#f0f2f7', marginBottom: 6 },
  successSub: { fontSize: 13, color: '#8a94b0', lineHeight: 1.5, marginBottom: 20 },
};

function PromoteModal({ targetNode, onClose }) {
  const [confirmed, setConfirmed] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  function handleConfirm() {
    setLoading(true);
    setTimeout(() => { setLoading(false); setConfirmed(true); }, 1000);
  }

  return (
    <div style={promoteModalStyles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={promoteModalStyles.modal}>
        <div style={promoteModalStyles.topBorder} />
        {confirmed ? (
          <div style={promoteModalStyles.successState}>
            <div style={promoteModalStyles.successIcon}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f5681e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
            </div>
            <div style={promoteModalStyles.successTitle}>{targetNode} is now Command</div>
            <div style={promoteModalStyles.successSub}>Incident journal authority transferred.<br />This node is now sequencing incident events.</div>
            <button style={{ ...promoteModalStyles.btnConfirm, width: '100%' }} onClick={onClose}>Done</button>
          </div>
        ) : (
          <>
            <div style={promoteModalStyles.icon}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f5681e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            <div style={promoteModalStyles.title}>Promote to Command?</div>
            <div style={promoteModalStyles.body}>
              This will transfer the incident journal authority to this vehicle. The previous command node will be demoted to responder.
            </div>
            <div style={promoteModalStyles.nodeRow}>
              <div>
                <div style={promoteModalStyles.nodeId}>{targetNode}</div>
                <div style={promoteModalStyles.nodeSub}>Responder → Command</div>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f5681e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="18 15 12 9 6 15"/>
              </svg>
            </div>
            <div style={promoteModalStyles.warningBox}>
              <div style={promoteModalStyles.warningText}>
                Promotion is manual. Ensure operational handoff is complete before confirming. Any unsynchronised outbox edits from the old command node may be delayed.
              </div>
            </div>
            <div style={promoteModalStyles.btnRow}>
              <button style={promoteModalStyles.btnCancel} onClick={onClose}>Cancel</button>
              <button style={promoteModalStyles.btnConfirm} onClick={handleConfirm} disabled={loading}>
                {loading ? 'Promoting…' : 'Confirm Promotion'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { PromoteModal });
