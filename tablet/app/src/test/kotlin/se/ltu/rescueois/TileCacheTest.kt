package se.ltu.rescueois

import org.junit.Assert.assertThrows
import org.junit.Test
import se.ltu.rescueois.data.local.TileCache

class TileCacheTest {

    @Test
    fun `read throws until backed by an actual cache file`() {
        val cache = TileCache("/tmp/does-not-exist.pmtiles")
        assertThrows(NotImplementedError::class.java) {
            cache.read(0L, 16)
        }
    }
}
