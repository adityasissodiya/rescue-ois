// SitePlanView.jsx — Pre-incident site plan and hazard notes

const sitePlanStyles = {
  root: { flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 },
  card: { background: '#252b3b', border: '1px solid #2e3650', borderRadius: 8, padding: '12px 14px' },
  cardTitle: { fontSize: 11, fontWeight: 600, color: '#4a5168', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 },
  mapBox: { background: '#141820', border: '1px solid #2e3650', borderRadius: 6, height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 6, marginBottom: 10 },
  mapLabel: { fontSize: 11, color: '#2e3650', fontFamily: "'JetBrains Mono', monospace" },
  row: { display: 'flex', gap: 12 },
  metaKey: { fontSize: 11, color: '#4a5168', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 500, marginBottom: 2 },
  metaVal: { fontSize: 13, color: '#f0f2f7', lineHeight: 1.4 },
  hazardRow: { display: 'flex', gap: 10, padding: '8px 0', borderBottom: '1px solid #1c2030', alignItems: 'flex-start' },
  hazardIcon: { width: 28, height: 28, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  hazardTitle: { fontSize: 13, fontWeight: 600, color: '#f0f2f7' },
  hazardSub: { fontSize: 11, color: '#8a94b0', marginTop: 2 },
  hazardLevel: { marginLeft: 'auto', fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 4 },
  attachRow: { display: 'flex', gap: 8, alignItems: 'center', padding: '7px 0', borderBottom: '1px solid #1c2030' },
  attachIcon: { color: '#4a5168' },
  attachName: { fontSize: 13, color: '#8a94b0', flex: 1 },
  attachMeta: { fontSize: 10, fontFamily: "'JetBrains Mono', monospace", color: '#4a5168' },
};

const HAZARDS = [
  { label: 'Fuel storage', detail: 'Basement, NE corner — diesel 2000L', level: 'HIGH', levelColor: '#e8302a', levelBg: 'rgba(232,48,42,0.12)' },
  { label: 'Confined spaces', detail: 'Sub-basement access hatch, W side', level: 'MED', levelColor: '#f5b21e', levelBg: 'rgba(245,178,30,0.12)' },
  { label: 'Electrical panels', detail: '3× panels, floor 2 and roof', level: 'MED', levelColor: '#f5b21e', levelBg: 'rgba(245,178,30,0.12)' },
  { label: 'Water mains', detail: 'Shutoff valve, street-side SW', level: 'LOW', levelColor: '#2db67d', levelBg: 'rgba(45,182,125,0.1)' },
];

const ATTACHMENTS = [
  { name: 'Floor plan — Industrivägen 14.pdf', size: '1.2 MB', date: '2026-01-08' },
  { name: 'Site photos — exterior.zip', size: '8.4 MB', date: '2026-01-08' },
  { name: 'Hazmat register excerpt.pdf', size: '340 KB', date: '2025-11-14' },
];

function SitePlanView() {
  return (
    <div style={sitePlanStyles.root}>
      <div style={sitePlanStyles.card}>
        <div style={sitePlanStyles.cardTitle}>Site map</div>
        <div style={sitePlanStyles.mapBox}>
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#2e3650" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
            <line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>
          </svg>
          <div style={sitePlanStyles.mapLabel}>MapLibre — offline tile cache</div>
          <div style={{ fontSize: 10, color: '#1e2538', fontFamily: "'JetBrains Mono', monospace" }}>57.7089°N 11.9746°E</div>
        </div>
        <div style={sitePlanStyles.row}>
          <div style={{ flex: 1 }}>
            <div style={sitePlanStyles.metaKey}>Address</div>
            <div style={sitePlanStyles.metaVal}>Industrivägen 14, Gothenburg</div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={sitePlanStyles.metaKey}>Object type</div>
            <div style={sitePlanStyles.metaVal}>Industrial warehouse, 3 floors</div>
          </div>
        </div>
        <div style={{ ...sitePlanStyles.row, marginTop: 8 }}>
          <div style={{ flex: 1 }}>
            <div style={sitePlanStyles.metaKey}>Plan version</div>
            <div style={{ ...sitePlanStyles.metaVal, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>v4 · 2026-01-08</div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={sitePlanStyles.metaKey}>Sync status</div>
            <div style={{ ...sitePlanStyles.metaVal, color: '#2db67d', fontSize: 12 }}>Up to date</div>
          </div>
        </div>
      </div>

      <div style={sitePlanStyles.card}>
        <div style={sitePlanStyles.cardTitle}>Hazards</div>
        {HAZARDS.map((h, i) => (
          <div key={i} style={{ ...sitePlanStyles.hazardRow, borderBottom: i === HAZARDS.length - 1 ? 'none' : undefined }}>
            <div style={{ ...sitePlanStyles.hazardIcon, background: h.levelBg }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={h.levelColor} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <div style={sitePlanStyles.hazardTitle}>{h.label}</div>
              <div style={sitePlanStyles.hazardSub}>{h.detail}</div>
            </div>
            <div style={{ ...sitePlanStyles.hazardLevel, color: h.levelColor, background: h.levelBg }}>{h.level}</div>
          </div>
        ))}
      </div>

      <div style={sitePlanStyles.card}>
        <div style={sitePlanStyles.cardTitle}>Attachments</div>
        {ATTACHMENTS.map((a, i) => (
          <div key={i} style={{ ...sitePlanStyles.attachRow, borderBottom: i === ATTACHMENTS.length - 1 ? 'none' : undefined }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4a5168" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
            <div style={sitePlanStyles.attachName}>{a.name}</div>
            <div style={sitePlanStyles.attachMeta}>{a.size} · {a.date}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { SitePlanView });
