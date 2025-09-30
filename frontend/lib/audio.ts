export type PlaybackItem = {
  buffer: AudioBuffer;
};

export class AudioPlaybackQueue {
  private context: AudioContext;
  private queue: PlaybackItem[] = [];
  private isPlaying = false;

  constructor(context: AudioContext) {
    this.context = context;
  }

  enqueueBuffer(buffer: AudioBuffer) {
    this.queue.push({ buffer });
    if (!this.isPlaying) {
      this.playNext();
    }
  }

  enqueuePCM16(base64Audio: string, sampleRate: number) {
    const audioBuffer = pcm16ToAudioBuffer(this.context, base64Audio, sampleRate);
    this.enqueueBuffer(audioBuffer);
  }

  private playNext() {
    const item = this.queue.shift();
    if (!item) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const source = this.context.createBufferSource();
    source.buffer = item.buffer;
    source.connect(this.context.destination);
    source.onended = () => {
      this.playNext();
    };
    source.start();
  }
}

export function decodeWavToBuffer(context: AudioContext, base64Audio: string) {
  const binary = Uint8Array.from(atob(base64Audio), (char) => char.charCodeAt(0));
  return context.decodeAudioData(binary.buffer.slice(0));
}

export function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

export function pcm16ToAudioBuffer(
  context: AudioContext,
  base64Audio: string,
  sampleRate: number
): AudioBuffer {
  const buffer = base64ToArrayBuffer(base64Audio);
  const int16 = new Int16Array(buffer.slice(0));
  const float32 = new Float32Array(int16.length);

  for (let i = 0; i < int16.length; i += 1) {
    float32[i] = int16[i] / 0x7fff;
  }

  const audioBuffer = context.createBuffer(1, float32.length, sampleRate);
  audioBuffer.copyToChannel(float32, 0, 0);
  return audioBuffer;
}
