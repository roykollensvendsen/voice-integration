package no.roykollensvendsen.voice

import android.Manifest
import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.util.Log

/**
 * Keeps the app, and the page's microphone and audio, alive with the screen off,
 * and listens for the wake word while no voice session is open.
 *
 * Being a foreground service of type microphone is what tells Android the
 * microphone may stay open in a pocket, and the wake lock keeps the processor
 * from sleeping under the conversation. ADR-VI-032, ADR-VI-033.
 */
class VoiceService : Service() {

    private var awake: PowerManager.WakeLock? = null
    private var listening: Thread? = null
    @Volatile private var keepListening = false

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(1, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        if (awake == null) {
            awake = (getSystemService(POWER_SERVICE) as PowerManager)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "voice:conversation")
                .apply { acquire() }
        }
        // One microphone at a time: while a session is open, the word is not listened for.
        if (intent?.action == LISTEN) sessionOpen = false
        if (!sessionOpen) startListening()
        return START_NOT_STICKY
    }

    @SuppressLint("MissingPermission")  // checked just below
    private fun startListening() {
        if (listening?.isAlive == true) return
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) return
        keepListening = true
        listening = Thread {
            val size = maxOf(
                AudioRecord.getMinBufferSize(RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT),
                WakeWord.CHUNK * 4,
            )
            val record = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                size,
            )
            val chunk = ShortArray(WakeWord.CHUNK)
            WakeWord(this).use { word ->
                record.startRecording()
                try {
                    while (keepListening) {
                        if (record.read(chunk, 0, chunk.size) != chunk.size) continue
                        if (word.hear(chunk) > WakeWord.THRESHOLD) {
                            keepListening = false
                            sessionOpen = true
                            Log.i(TAG, "heard the wake word")
                            main.post { onWake?.invoke() }
                        }
                    }
                } finally {
                    record.stop()
                    record.release()
                }
            }
        }.apply { name = "wake-word"; start() }
    }

    private fun stopListening() {
        keepListening = false
        listening?.join(1000)
        listening = null
    }

    override fun onCreate() {
        super.onCreate()
        running = this
    }

    override fun onDestroy() {
        running = null
        stopListening()
        awake?.release()
        awake = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun notification(): Notification {
        val channel = NotificationChannel("voice", getString(R.string.channel), NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
        )
        return Notification.Builder(this, "voice")
            .setContentTitle(getString(R.string.listening_title))
            .setContentText(getString(R.string.listening_text))
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(open)
            .setOngoing(true)
            .build()
    }

    companion object {
        private const val TAG = "WakeWord"
        private const val RATE = 16_000
        private const val LISTEN = "no.roykollensvendsen.voice.LISTEN"
        private val main = Handler(Looper.getMainLooper())
        @Volatile private var running: VoiceService? = null
        @Volatile private var sessionOpen = false

        /** What to do when the word is heard: the activity tells the page. */
        @Volatile var onWake: (() -> Unit)? = null

        /** Listen for the word again: no session is open. */
        fun listen(context: Context) {
            context.startForegroundService(Intent(context, VoiceService::class.java).setAction(LISTEN))
        }

        /**
         * Stop listening for the word: a session takes the microphone. Done at
         * once, before the page asks for the microphone, not when Android gets
         * round to delivering a message.
         */
        fun pause() {
            sessionOpen = true
            running?.stopListening()
        }
    }
}
