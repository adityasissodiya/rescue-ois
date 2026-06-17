package org.review.rescueois.domain

/**
 * Local sync state, surfaced by SyncStatusBar.
 */
data class SyncState(
    val connected: Boolean,
    val lastSyncEpochMs: Long?,
    val pendingOutboxCount: Int
)
