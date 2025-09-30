class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) {
      return true;
    }

    const channelData = input[0];
    if (channelData) {
      // Transfer a copy of the data back to the main thread.
      this.port.postMessage(channelData.slice());
    }

    return true;
  }
}

registerProcessor("pcm-processor", PCMProcessor);
