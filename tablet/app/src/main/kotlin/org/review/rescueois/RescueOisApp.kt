package org.review.rescueois

import android.app.Application

/**
 * Application entry point. Wires up Room, the EdgeApiClient, and SyncManager
 * once the host process starts.
 */
class RescueOisApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // TODO: initialize AppDatabase, EdgeApiClient, SyncManager
    }
}
