package se.ltu.rescueois.domain

/**
 * Domain model: a known operational site.
 */
data class Site(
    val id: String,
    val name: String,
    val latitude: Double,
    val longitude: Double,
    val metadata: Map<String, Any> = emptyMap()
)
