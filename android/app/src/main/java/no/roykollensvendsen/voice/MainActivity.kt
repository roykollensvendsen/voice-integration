package no.roykollensvendsen.voice

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.webkit.JavascriptInterface
import android.webkit.GeolocationPermissions
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText

/**
 * Today's voice page, unchanged, kept going with the screen off.
 *
 * The page holds every behaviour of the voice. This activity adds only what a
 * page cannot have: the microphone handed to it by Android, and a service that
 * keeps the process and its audio alive in a pocket. ADR-VI-032.
 */
class MainActivity : Activity() {

    private lateinit var page: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(saved: Bundle?) {
        super.onCreate(saved)
        page = WebView(this)
        page.settings.javaScriptEnabled = true
        page.settings.domStorageEnabled = true
        // The voice speaks before anybody touches the page again.
        page.settings.mediaPlaybackRequiresUserGesture = false
        page.webViewClient = object : WebViewClient() {
            override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                // A page that cannot be reached is most often a wrong address,
                // so it is asked for again rather than left on an error.
                if (request.isForMainFrame) askForAddress()
            }
        }
        page.webChromeClient = object : WebChromeClient() {
            override fun onGeolocationPermissionsShowPrompt(
                origin: String,
                callback: GeolocationPermissions.Callback,
            ) {
                // The page's own question, answered by what Android was told.
                callback.invoke(origin, hasLocation(), false)
            }

            override fun onPermissionRequest(request: PermissionRequest) {
                // Only the microphone, and only once Android has given it to the app.
                val audio = PermissionRequest.RESOURCE_AUDIO_CAPTURE
                if (audio in request.resources && hasMicrophone()) {
                    request.grant(arrayOf(audio))
                } else {
                    request.deny()
                }
            }
        }
        // The page tells the app when a session takes the microphone and when it
        // gives it back, so the wake word is listened for only in between.
        page.addJavascriptInterface(Microphone(), "VoiceApp")
        VoiceService.onWake = {
            page.evaluateJavascript("window.wakeWordHeard && window.wakeWordHeard()", null)
        }
        // A page out of sight is normally given a low priority and paused.
        // This one is the conversation, so it keeps its priority.
        page.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_IMPORTANT, false)
        setContentView(page)

        askForPermissions()
        val address = Settings.address(this)
        if (address == null) askForAddress() else page.loadUrl(address)
        testTheWord(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        testTheWord(intent)
    }

    /**
     * Run a recording through the wake-word models, log how sure they were,
     * and wake the page as the real word would, so the whole path can be
     * checked on a phone with known speech:
     * adb shell am start -n no.roykollensvendsen.voice/.MainActivity --es wake_test clip.raw
     * with clip.raw, 16 kHz mono 16-bit, in the app's own files folder.
     */
    private fun testTheWord(intent: Intent?) {
        val name = intent?.getStringExtra("wake_test") ?: return
        Thread {
            val bytes = getExternalFilesDir(null)!!.resolve(name).readBytes()
            val silence = ShortArray(32_000)
            val speech = ShortArray(bytes.size / 2) { (bytes[2 * it].toInt() and 0xff or (bytes[2 * it + 1].toInt() shl 8)).toShort() }
            val audio = silence + speech + silence
            var peak = 0f
            WakeWord(this).use { word ->
                for (start in 0..audio.size - WakeWord.CHUNK step WakeWord.CHUNK) {
                    peak = maxOf(peak, word.hear(audio.copyOfRange(start, start + WakeWord.CHUNK)))
                }
            }
            Log.i("WakeWord", "test $name: peak %.3f".format(peak))
            // Heard in a recording is heard: the page opens a session as it would.
            if (peak > WakeWord.THRESHOLD) VoiceService.onWake?.let { runOnUiThread(it) }
        }.start()
    }

    /** What the page calls when it takes the microphone, and when it gives it back. */
    inner class Microphone {
        @JavascriptInterface
        fun sessionOpened() = VoiceService.pause()

        @JavascriptInterface
        fun sessionClosed() = VoiceService.listen(this@MainActivity)
    }

    override fun onStart() {
        super.onStart()
        // Android starts a microphone service only while the app is on screen.
        if (hasMicrophone()) startForegroundService(Intent(this, VoiceService::class.java))
    }

    // onPause and onStop leave the page running on purpose: pausing it would
    // stop the conversation the moment the screen goes off.

    override fun onDestroy() {
        VoiceService.onWake = null
        // A change of screen or theme is not the end of the conversation.
        if (!isChangingConfigurations) stopService(Intent(this, VoiceService::class.java))
        page.destroy()
        super.onDestroy()
    }

    override fun onRequestPermissionsResult(code: Int, asked: Array<out String>, given: IntArray) {
        super.onRequestPermissionsResult(code, asked, given)
        if (hasMicrophone()) startForegroundService(Intent(this, VoiceService::class.java))
    }

    @Deprecated("Back leaves the page where it is, as a browser's back button would not.")
    override fun onBackPressed() {
        if (page.canGoBack()) page.goBack() else moveTaskToBack(true)
    }

    private fun hasMicrophone() =
        checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    private fun hasLocation() =
        checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    private fun askForPermissions() {
        val wanted = mutableListOf(
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.ACCESS_FINE_LOCATION,
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            wanted += Manifest.permission.POST_NOTIFICATIONS
        }
        val missing = wanted.filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) requestPermissions(missing.toTypedArray(), 1)
    }

    /** The bridge's address is the person's own, so it is asked for, not built in. */
    private fun askForAddress() {
        val field = EditText(this).apply {
            hint = getString(R.string.ask_address_hint)
            setText(Settings.address(this@MainActivity) ?: "")
        }
        AlertDialog.Builder(this)
            .setTitle(R.string.ask_address)
            .setView(field)
            .setCancelable(false)
            .setPositiveButton(R.string.save) { _, _ ->
                val address = field.text.toString().trim()
                Settings.save(this, address)
                page.loadUrl(address)
            }
            .show()
    }
}
