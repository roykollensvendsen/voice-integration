package no.roykollensvendsen.voice

import android.content.Context

/** The one setting: where the bridge's page is. */
object Settings {
    private const val FILE = "voice"
    private const val ADDRESS = "address"

    fun address(context: Context): String? =
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).getString(ADDRESS, null)?.takeIf { it.isNotBlank() }

    fun save(context: Context, address: String) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().putString(ADDRESS, address).apply()
    }
}
