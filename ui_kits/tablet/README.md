# Tablet UI Kit

Conceptual hi-fidelity UI kit for the **field tablet** (Tier 3) described in the Tiered Sync paper. This is a **proposed design** — no production tablet UI codebase was provided.

## Screens

1. **Incident Overview** — active incident, sync state, quick actions
2. **Fleet View** — all vehicles/nodes, their roles and sync status
3. **Site Plan** — pre-incident plan viewer with map placeholder and hazard notes
4. **Outbox** — queued field edits waiting to forward to command vehicle
5. **Promote Modal** — command promotion confirmation flow

## Design decisions

- Dark mode throughout — field tablets are used in varied light conditions including night operations
- Minimum 44px touch targets everywhere
- Sync status always visible in the top bar
- OFFLINE state degrades gracefully — all locally cached data stays accessible
- IBM Plex Sans for UI, JetBrains Mono for data/IDs/timestamps
- No maps drawn — map area is a placeholder (would use MapLibre with dark vector tiles)

## Files

- `index.html` — interactive click-through prototype
- `TopBar.jsx` — sync status bar, node ID, role badge
- `IncidentView.jsx` — incident overview screen
- `FleetView.jsx` — vehicle fleet list
- `SitePlanView.jsx` — site plan/hazard card view
- `OutboxView.jsx` — outbox queue
- `PromoteModal.jsx` — promote-to-command modal
