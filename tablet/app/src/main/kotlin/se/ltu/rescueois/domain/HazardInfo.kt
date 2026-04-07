package se.ltu.rescueois.domain

/**
 * Domain model: hazard information for a site, derived from master.hazards.
 */
data class HazardInfo(
    val id: String,
    val siteId: String,
    val substance: String,
    val storageInfo: Map<String, Any> = emptyMap()
)
