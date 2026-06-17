package org.review.rescueois.data.remote

/**
 * Coordinates baseline pulls, field edit submissions, and incident polling
 * against the local K430 ops-api.
 */
class SyncManager(private val client: EdgeApiClient) {

    suspend fun syncBaseline() {
        // TODO: GET /api/bootstrap; persist into local Room cache
        throw NotImplementedError()
    }

    suspend fun submitFieldEdit(edit: Map<String, Any>) {
        // TODO: POST /api/events with idempotency key; on failure, persist into local outbox
        throw NotImplementedError()
    }

    suspend fun pollEvents(afterSeq: Long) {
        // TODO: poll incident events newer than afterSeq, update local IncidentDao
        throw NotImplementedError()
    }
}
