/**
 * Pure JavaScript PCM 16kHz Mono WAV Recorder & Encoder.
 * Captures clean, uncompressed 16-bit linear PCM audio compatible with all STT engines (Sarvam Saaras v3, Whisper, etc.).
 */

export class WavAudioRecorder {
  constructor() {
    this.audioContext = null;
    this.mediaStream = null;
    this.scriptProcessor = null;
    this.audioInput = null;
    this.recordedBuffers = [];
    this.sampleRate = 16000;
  }

  async start() {
    this.recordedBuffers = [];

    // Request microphone access
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    this.audioContext = new AudioContextClass({ sampleRate: 16000 });
    this.sampleRate = this.audioContext.sampleRate;

    this.audioInput = this.audioContext.createMediaStreamSource(this.mediaStream);
    // Buffer size: 4096, 1 input channel, 1 output channel
    this.scriptProcessor = this.audioContext.createScriptProcessor(4096, 1, 1);

    this.scriptProcessor.onaudioprocess = (event) => {
      const inputBuffer = event.inputBuffer.getChannelData(0);
      // Clone buffer data
      this.recordedBuffers.push(new Float32Array(inputBuffer));
    };

    this.audioInput.connect(this.scriptProcessor);
    this.scriptProcessor.connect(this.audioContext.destination);
  }

  async stop() {
    if (this.scriptProcessor && this.audioInput) {
      this.audioInput.disconnect();
      this.scriptProcessor.disconnect();
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      await this.audioContext.close();
    }

    // Merge and encode buffers to 16-bit PCM WAV Blob
    return this.encodeWAV(this.recordedBuffers, this.sampleRate);
  }

  encodeWAV(buffers, sampleRate) {
    // 1. Calculate total length
    let totalLength = 0;
    for (let i = 0; i < buffers.length; i++) {
      totalLength += buffers[i].length;
    }

    // 2. Merge all float32 samples
    const mergedSamples = new Float32Array(totalLength);
    let offset = 0;
    for (let i = 0; i < buffers.length; i++) {
      mergedSamples.set(buffers[i], offset);
      offset += buffers[i].length;
    }

    // 3. Create 16-bit PCM WAV header (44 bytes) + data
    const buffer = new ArrayBuffer(44 + mergedSamples.length * 2);
    const view = new DataView(buffer);

    // RIFF identifier
    this.writeString(view, 0, 'RIFF');
    // file length minus RIFF identifier & length
    view.setUint32(4, 36 + mergedSamples.length * 2, true);
    // RIFF type
    this.writeString(view, 8, 'WAVE');
    // format chunk identifier
    this.writeString(view, 12, 'fmt ');
    // format chunk length
    view.setUint32(16, 16, true);
    // sample format (1 = raw PCM)
    view.setUint16(20, 1, true);
    // channel count (1 = mono)
    view.setUint16(22, 1, true);
    // sample rate (16000 Hz)
    view.setUint32(24, sampleRate, true);
    // byte rate (sampleRate * blockAlign = 16000 * 2 = 32000)
    view.setUint32(28, sampleRate * 2, true);
    // block align (channel count * bytes per sample = 1 * 2 = 2)
    view.setUint16(32, 2, true);
    // bits per sample (16-bit)
    view.setUint16(34, 16, true);
    // data chunk identifier
    this.writeString(view, 36, 'data');
    // data chunk length
    view.setUint32(40, mergedSamples.length * 2, true);

    // 4. Convert float32 [-1.0, 1.0] to 16-bit PCM signed integer [-32768, 32767]
    let index = 44;
    for (let i = 0; i < mergedSamples.length; i++) {
      let s = Math.max(-1, Math.min(1, mergedSamples[i]));
      view.setInt16(index, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      index += 2;
    }

    return new Blob([view], { type: 'audio/wav' });
  }

  writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }
}
