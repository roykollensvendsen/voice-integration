package no.roykollensvendsen.voice

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
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
        // A page out of sight is normally given a low priority and paused.
        // This one is the conversation, so it keeps its priority.
        page.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_IMPORTANT, false)
        setContentView(page)

        askForPermissions()
        val address = Settings.address(this)
        if (address == null) askForAddress() else page.loadUrl(address)
    }

    override fun onStart() {
        super.onStart()
        // Android starts a microphone service only while the app is on screen.
        if (hasMicrophone()) startForegroundService(Intent(this, VoiceService::class.java))
    }

    // onPause and onStop leave the page running on purpose: pausing it would
    // stop the conversation the moment the screen goes off.

    override fun onDestroy() {
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

    private fun askForPermissions() {
        val wanted = mutableListOf(Manifest.permission.RECORD_AUDIO)
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
