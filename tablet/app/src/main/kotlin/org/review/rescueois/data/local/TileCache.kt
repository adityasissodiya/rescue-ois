package org.review.rescueois.data.local

/**
 * Local PMTiles cache wrapper. Backs OfflineTileProvider with byte-range
 * reads from a single PMTiles file pinned to the device's encrypted storage.
 */
class TileCache(private val cachePath: String) {
    fun read(offset: Long, length: Int): ByteArray {
        // TODO: open cachePath, seek to offset, read length bytes
        throw NotImplementedError()
    }
}
