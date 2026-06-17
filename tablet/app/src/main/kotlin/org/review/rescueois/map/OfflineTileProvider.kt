package org.review.rescueois.map

import org.review.rescueois.data.local.TileCache

/**
 * Serves vector tiles from the local PMTiles cache to MapLibre.
 */
class OfflineTileProvider(private val cache: TileCache) {
    fun fetchTile(z: Int, x: Int, y: Int): ByteArray {
        // TODO: compute PMTiles offset for (z,x,y), call cache.read(...)
        throw NotImplementedError()
    }
}
