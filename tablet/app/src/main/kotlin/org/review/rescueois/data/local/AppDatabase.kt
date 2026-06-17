package org.review.rescueois.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

/**
 * Room database for the tablet local cache.
 */
@Database(
    entities = [],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun siteDao(): SiteDao
    abstract fun incidentDao(): IncidentDao
}
