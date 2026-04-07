package se.ltu.rescueois

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertThrows
import org.junit.Test
import se.ltu.rescueois.data.remote.EdgeApiClient
import se.ltu.rescueois.data.remote.SyncManager

class SyncManagerTest {

    private val noopClient = object : EdgeApiClient {
        override suspend fun getBootstrap(): Map<String, Any> = emptyMap()
        override suspend fun search(q: String): Map<String, Any> = emptyMap()
        override suspend fun postEvent(event: Map<String, Any>): Map<String, Any> = emptyMap()
        override suspend fun getFile(path: String): okhttp3.ResponseBody =
            throw NotImplementedError()
    }

    @Test
    fun `syncBaseline is not yet implemented`() = runTest {
        val sm = SyncManager(noopClient)
        assertThrows(NotImplementedError::class.java) {
            kotlinx.coroutines.runBlocking { sm.syncBaseline() }
        }
    }
}
