package no.roykollensvendsen.voice

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import java.nio.FloatBuffer

/**
 * Hears whether "Hey Jarvis" was said, and nothing else. ADR-VI-033.
 *
 * openWakeWord's three models, run as openWakeWord runs them: raw audio to a
 * mel spectrogram, 76 mel frames to one 96-number embedding, and the last 16
 * embeddings to a score between 0 and 1. Audio comes in 80 ms at a time and
 * never leaves this class.
 */
class WakeWord(context: Context) : AutoCloseable {

    private val env = OrtEnvironment.getEnvironment()
    private val mel = open(context, "melspectrogram.onnx")
    private val embedding = open(context, "embedding_model.onnx")
    private val wake = open(context, "hey_jarvis_v0.1.onnx")

    /** The last stretch of raw audio: one chunk, and three hops of context. */
    private var raw = FloatArray(0)
    private val mels = ArrayDeque<FloatArray>().apply { repeat(MEL_FRAMES) { add(FloatArray(MEL_BINS) { 1f }) } }
    private val embeddings = ArrayDeque<FloatArray>().apply { repeat(EMBEDDINGS) { add(FloatArray(EMBEDDING_SIZE)) } }

    /** Feed one chunk of [CHUNK] samples at 16 kHz, and get how sure the model is that the word was said. */
    fun hear(chunk: ShortArray): Float {
        raw = (raw + FloatArray(chunk.size) { chunk[it].toFloat() }).takeLast(CHUNK + CONTEXT).toFloatArray()
        if (raw.size < CHUNK + CONTEXT) return 0f
        for (frame in melFrames(raw)) {
            mels.addLast(frame)
            if (mels.size > MEL_FRAMES) mels.removeFirst()
        }
        embeddings.addLast(embed())
        if (embeddings.size > EMBEDDINGS) embeddings.removeFirst()
        return score()
    }

    /** Forget what was heard, so a new listen starts clean. */
    fun reset() {
        raw = FloatArray(0)
    }

    private fun melFrames(audio: FloatArray): List<FloatArray> {
        OnnxTensor.createTensor(env, FloatBuffer.wrap(audio), longArrayOf(1, audio.size.toLong())).use { input ->
            mel.run(mapOf(mel.inputNames.first() to input)).use { out ->
                val values = (out[0].value as Array<*>)  // [time][1][frames][32]
                val frames = ((values[0] as Array<*>)[0] as Array<*>)
                // openWakeWord's own scaling of the spectrogram.
                return frames.map { row -> (row as FloatArray).map { it / 10f + 2f }.toFloatArray() }
            }
        }
    }

    private fun embed(): FloatArray {
        val flat = FloatArray(MEL_FRAMES * MEL_BINS)
        mels.forEachIndexed { i, frame -> frame.copyInto(flat, i * MEL_BINS) }
        val shape = longArrayOf(1, MEL_FRAMES.toLong(), MEL_BINS.toLong(), 1)
        OnnxTensor.createTensor(env, FloatBuffer.wrap(flat), shape).use { input ->
            embedding.run(mapOf(embedding.inputNames.first() to input)).use { out ->
                @Suppress("UNCHECKED_CAST")
                val values = out[0].value as Array<Array<Array<FloatArray>>>  // [1][1][1][96]
                return values[0][0][0]
            }
        }
    }

    private fun score(): Float {
        val flat = FloatArray(EMBEDDINGS * EMBEDDING_SIZE)
        embeddings.forEachIndexed { i, e -> e.copyInto(flat, i * EMBEDDING_SIZE) }
        val shape = longArrayOf(1, EMBEDDINGS.toLong(), EMBEDDING_SIZE.toLong())
        OnnxTensor.createTensor(env, FloatBuffer.wrap(flat), shape).use { input ->
            wake.run(mapOf(wake.inputNames.first() to input)).use { out ->
                @Suppress("UNCHECKED_CAST")
                return (out[0].value as Array<FloatArray>)[0][0]
            }
        }
    }

    private fun open(context: Context, name: String): OrtSession =
        env.createSession(context.assets.open("wakeword/$name").use { it.readBytes() })

    override fun close() {
        mel.close()
        embedding.close()
        wake.close()
    }

    companion object {
        /** 80 ms of audio at 16 kHz: what the models expect each time. */
        const val CHUNK = 1280
        private const val CONTEXT = 160 * 3
        private const val MEL_FRAMES = 76
        private const val MEL_BINS = 32
        private const val EMBEDDINGS = 16
        private const val EMBEDDING_SIZE = 96

        /** How sure the model must be. 0.5 is openWakeWord's own default. */
        const val THRESHOLD = 0.5f
    }
}
