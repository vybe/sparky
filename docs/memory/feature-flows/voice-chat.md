# Feature: Voice Chat

## Overview
Voice-in, voice-out conversation using Ultravox (speech understanding) and Chatterbox TTS (speech synthesis).

## User Story
As a user, I want to speak to an AI and hear spoken responses so that I can have natural voice conversations.

## Entry Points
- **UI**: `src/components/VoiceChat.vue:252` - Voice interface with record button
- **API**: Ultravox at `:11100/v1/chat/completions`, Chatterbox at `:11004/tts`

## Frontend Layer

### Components
- `src/components/VoiceChat.vue:7-12` - Voice list (28 Chatterbox voices)
- `src/components/VoiceChat.vue:262-271` - Voice selector dropdown
- `src/components/VoiceChat.vue:281-296` - Record button (toggle)
- `src/components/VoiceChat.vue:306-335` - Conversation history

**Key State:**
```javascript
selectedVoice  // ref('Emily') - TTS voice name
isRecording    // ref(false) - Currently recording
isProcessing   // ref(false) - Processing audio
status         // ref('Ready') - Status message
conversation   // ref([]) - Chat history with audio URLs
```

### Audio Pipeline

**1. Recording:**
```javascript
// src/components/VoiceChat.vue:85-131
const stream = await navigator.mediaDevices.getUserMedia({
  audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true }
})
mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
```

**2. WAV Conversion:**
```javascript
// src/components/VoiceChat.vue:26-83
async function convertToWav(audioBlob) {
  // Decode with Web Audio API
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
  // Resample to 16kHz mono
  const offlineContext = new OfflineAudioContext(1, duration * 16000, 16000)
  // Create WAV header + PCM data
  // Returns Blob with type 'audio/wav'
}
```

### API Calls

**Ultravox - Speech Understanding:**
```javascript
// src/components/VoiceChat.vue:166-180
await fetch(`${ULTRAVOX_URL}/v1/chat/completions`, {
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
// Response: { choices: [{ message: { content: "text response" } }] }
```

**Chatterbox - Text-to-Speech:**
```javascript
// src/components/VoiceChat.vue:192-199
await fetch(`${CHATTERBOX_URL}/tts`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: responseText,
    voice_mode: 'predefined',
    predefined_voice_id: `${selectedVoice.value}.wav`
  })
})
// Response: audio/wav blob
```

## Data Flow

1. **User taps Record**: `startRecording()` requests microphone access
2. **Recording starts**: MediaRecorder captures WebM/Opus audio
3. **User taps Stop**: `stopRecording()` triggers `onstop` handler
4. **WAV conversion**: `convertToWav()` resamples to 16kHz mono
5. **Ultravox call**: Audio sent as base64, returns text response
6. **TTS call**: Text sent to Chatterbox, returns WAV audio
7. **Playback**: Response audio auto-plays, added to conversation

```
[Tap Record] --> MediaRecorder --> WebM/Opus Blob
                                        |
                               convertToWav()
                                        |
                               Base64 encode
                                        |
          POST /v1/chat/completions --> "text response"
                                        |
                    POST /tts --------> WAV Blob
                                        |
                         Auto-play + Add to conversation
```

## External Services

### Ultravox (port 8100 / tunnel 11100)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/chat/completions` | POST | Speech-to-text-to-response |

**Request Format:**
```json
{
  "model": "fixie-ai/ultravox-v0_3",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "input_audio", "input_audio": {"data": "<base64>", "format": "wav"}},
      {"type": "text", "text": "prompt"}
    ]
  }],
  "max_tokens": 500
}
```

### Chatterbox TTS (port 8004 / tunnel 11004)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/tts` | POST | Text to speech synthesis |
| `/voices` | GET | List available voices |

**Request Format:**
```json
{
  "text": "Response text",
  "voice_mode": "predefined",
  "predefined_voice_id": "Emily.wav"
}
```

**Available Voices (28):**
Abigail, Adrian, Alexander, Alice, Austin, Axel, Connor, Cora, Elena, Eli, Emily, Everett, Gabriel, Gianna, Henry, Ian, Jade, Jeremiah, Jordan, Julian, Layla, Leonardo, Michael, Miles, Olivia, Ryan, Taylor, Thomas

## Audio Format Requirements

| Stage | Format | Sample Rate | Channels |
|-------|--------|-------------|----------|
| Recording | WebM/Opus | Device default | Mono |
| Ultravox Input | WAV/PCM | 16kHz | Mono |
| TTS Output | WAV | Varies | Mono |

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| Mic denied | getUserMedia rejects | Error message | User grants permission |
| Conversion fails | convertToWav throws | Error message + status reset | Retry recording |
| Ultravox fails | Response not ok | Error in conversation | Retry |
| TTS fails | Response not ok | Error message | Retry |

## Configuration

- **ULTRAVOX_URL**: `src/config.js:8` defaults to `http://localhost:11100`
- **CHATTERBOX_URL**: `src/config.js:9` defaults to `http://localhost:11004`

## Browser Requirements

- **MediaDevices API**: For microphone access
- **Web Audio API**: For audio resampling
- **OfflineAudioContext**: For WAV creation

## Related Flows

- **Upstream**: None
- **Downstream**: None (standalone feature)
