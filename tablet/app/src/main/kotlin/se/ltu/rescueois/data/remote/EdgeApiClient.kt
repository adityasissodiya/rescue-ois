package se.ltu.rescueois.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Retrofit interface mirroring ops-api endpoints exposed by the local K430.
 */
interface EdgeApiClient {

    @GET("api/bootstrap")
    suspend fun getBootstrap(): Map<String, Any>

    @GET("api/search")
    suspend fun search(@Query("q") q: String): Map<String, Any>

    @POST("api/events")
    suspend fun postEvent(@Body event: Map<String, Any>): Map<String, Any>

    @GET("files/{path}")
    suspend fun getFile(@Path("path") path: String): okhttp3.ResponseBody
}
