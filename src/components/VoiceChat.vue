<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useConfig } from '../config.js'

const { ultravoxUrl: ULTRAVOX_URL, chatterboxUrl: CHATTERBOX_URL } = useConfig()

const voices = [
  'Emily', 'Adrian', 'Olivia', 'Michael', 'Alice', 'Alexander',
  'Abigail', 'Austin', 'Axel', 'Connor', 'Cora', 'Elena', 'Eli',
  'Everett', 'Gabriel', 'Gianna', 'Henry', 'Ian', 'Jade', 'Jeremiah',
  'Jordan', 'Julian', 'Layla', 'Leonardo', 'Miles', 'Ryan', 'Taylor', 'Thomas'
]

const selectedVoice = ref('Emily')
const isRecording = ref(false)
const isProcessing = ref(false)
const status = ref('Ready')
const error = ref('')
const conversation = ref([])

let mediaRecorder = null
let audioChunks = []
let audioContext = null

// Convert audio blob to WAV format using Web Audio API
async function convertToWav(audioBlob) {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)()
  }

  const arrayBuffer = await audioBlob.arrayBuffer()
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)

  // Convert to WAV
  const numChannels = 1 // Mono
  const sampleRate = 16000 // 16kHz is good for speech
  const bitsPerSample = 16

  // Resample to 16kHz mono
  const offlineContext = new OfflineAudioContext(numChannels, audioBuffer.duration * sampleRate, sampleRate)
  const source = offlineContext.createBufferSource()
  source.buffer = audioBuffer
  source.connect(offlineContext.destination)
  source.start()

  const resampledBuffer = await offlineContext.startRendering()
  const samples = resampledBuffer.getChannelData(0)

  // Create WAV file
  const wavBuffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(wavBuffer)

  // WAV header
  const writeString = (offset, str) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true) // Subchunk1Size
  view.setUint16(20, 1, true) // AudioFormat (PCM)
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * numChannels * bitsPerSample / 8, true) // ByteRate
  view.setUint16(32, numChannels * bitsPerSample / 8, true) // BlockAlign
  view.setUint16(34, bitsPerSample, true)
  writeString(36, 'data')
  view.setUint32(40, samples.length * 2, true)

  // Write samples
  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true)
    offset += 2
  }

  return new Blob([wavBuffer], { type: 'audio/wav' })
}

async function startRecording() {
  error.value = ''

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true
      }
    })

    // Try to use wav/pcm if supported, otherwise use default
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm'

    mediaRecorder = new MediaRecorder(stream, { mimeType })
    audioChunks = []

    mediaRecorder.ondataavailable = (e) => {
      audioChunks.push(e.data)
    }

    mediaRecorder.onstop = async () => {
      const rawBlob = new Blob(audioChunks, { type: mimeType })
      stream.getTracks().forEach(track => track.stop())

      status.value = '🔄 Converting audio...'
      try {
        const wavBlob = await convertToWav(rawBlob)
        await processAudio(wavBlob)
      } catch (e) {
        error.value = 'Audio conversion failed: ' + e.message
        status.value = 'Ready'
        isProcessing.value = false
      }
    }

    mediaRecorder.start()
    isRecording.value = true
    status.value = '🎤 Recording... Click to stop'
  } catch (e) {
    error.value = 'Microphone access denied: ' + e.message
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording.value) {
    mediaRecorder.stop()
    isRecording.value = false
    status.value = 'Processing...'
  }
}

function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

async function processAudio(audioBlob) {
  isProcessing.value = true

  try {
    // Convert blob to base64
    const base64Audio = await blobToBase64(audioBlob)

    // Add user message placeholder
    conversation.value.push({
      role: 'user',
      content: '[Audio message]',
      audio: URL.createObjectURL(audioBlob)
    })

    status.value = '🧠 Understanding speech...'

    // Send to Ultravox
    const ultravoxRes = await fetch(`${ULTRAVOX_URL}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'fixie-ai/ultravox-v0_3',
        messages: [{
          role: 'user',
          content: [
            { type: 'input_audio', input_audio: { data: base64Audio, format: 'wav' }},
            { type: 'text', text: 'Please respond naturally to what was said.' }
          ]
        }],
        max_tokens: 500
      })
    })

    if (!ultravoxRes.ok) {
      throw new Error('Ultravox failed: ' + await ultravoxRes.text())
    }

    const ultravoxData = await ultravoxRes.json()
    const responseText = ultravoxData.choices?.[0]?.message?.content || 'No response'

    status.value = '🔊 Generating speech...'

    // Send to Chatterbox TTS
    const ttsRes = await fetch(`${CHATTERBOX_URL}/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: responseText,
        voice_mode: 'predefined',
        predefined_voice_id: `${selectedVoice.value}.wav`
      })
    })

    if (!ttsRes.ok) {
      throw new Error('TTS failed: ' + await ttsRes.text())
    }

    const audioResponseBlob = await ttsRes.blob()
    const audioUrl = URL.createObjectURL(audioResponseBlob)

    // Add assistant response
    conversation.value.push({
      role: 'assistant',
      content: responseText,
      audio: audioUrl
    })

    // Auto-play response
    const audio = new Audio(audioUrl)
    audio.play()

    status.value = 'Ready'

  } catch (e) {
    error.value = e.message
    status.value = 'Error'
  } finally {
    isProcessing.value = false
  }
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      const base64 = reader.result.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

function playAudio(url) {
  const audio = new Audio(url)
  audio.play()
}

function clearConversation() {
  conversation.value = []
}
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <!-- Header -->
    <div class="bg-gray-800 rounded-lg p-4">
      <h2 class="text-lg font-semibold mb-4">Voice Chat</h2>
      <p class="text-gray-400 text-sm mb-4">
        Talk to AI using Ultravox (speech understanding) + Chatterbox (TTS)
      </p>

      <!-- Voice Selection -->
      <div class="flex items-center gap-4 mb-4">
        <label class="text-sm text-gray-400">Voice:</label>
        <select
          v-model="selectedVoice"
          class="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
        >
          <option v-for="voice in voices" :key="voice" :value="voice">
            {{ voice }}
          </option>
        </select>
        <button
          @click="clearConversation"
          class="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
        >
          Clear
        </button>
      </div>

      <!-- Record Button -->
      <button
        @click="toggleRecording"
        :disabled="isProcessing"
        :class="[
          'w-full py-6 rounded-lg font-medium text-xl transition-all',
          isRecording
            ? 'bg-red-600 hover:bg-red-700 animate-pulse'
            : isProcessing
              ? 'bg-gray-600 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700'
        ]"
      >
        <span v-if="isRecording">🎤 Recording... Tap to Stop</span>
        <span v-else-if="isProcessing">⏳ Processing...</span>
        <span v-else>🎤 Tap to Talk</span>
      </button>

      <!-- Status -->
      <div class="text-center text-gray-400 text-sm mt-3">{{ status }}</div>

      <!-- Error -->
      <div v-if="error" class="text-red-400 text-sm mt-2 text-center">{{ error }}</div>
    </div>

    <!-- Conversation -->
    <div class="space-y-4">
      <div v-if="conversation.length === 0" class="text-center text-gray-500 py-8">
        Tap the button and speak to start a conversation
      </div>

      <div
        v-for="(msg, idx) in conversation"
        :key="idx"
        :class="[
          'rounded-lg p-4',
          msg.role === 'user' ? 'bg-blue-900/50 ml-8' : 'bg-gray-800 mr-8'
        ]"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1">
            <div class="text-xs text-gray-500 mb-1">
              {{ msg.role === 'user' ? 'You' : selectedVoice }}
            </div>
            <div class="text-gray-100">{{ msg.content }}</div>
          </div>
          <button
            v-if="msg.audio"
            @click="playAudio(msg.audio)"
            class="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm shrink-0"
          >
            🔊 Play
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
