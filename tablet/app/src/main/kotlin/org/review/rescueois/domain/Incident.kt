package org.review.rescueois.domain

/**
 * Domain model: an active incident as observed by this tablet.
 */
data class Incident(
    val id: String,
    val name: String,
    val status: String,
    val lastEventSeq: Long
)
