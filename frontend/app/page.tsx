"use client";

import { useState, useEffect, useRef } from "react";
import { Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import AudioLinesOrb from "@/components/AudioLinesOrb";

type AssistantState = "idle" | "listening" | "processing" | "speaking";

export default function Home() {
  const [state, setState] = useState<AssistantState>("idle");
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [assistantText, setAssistantText] = useState("");
  const [error, setError] = useState("");
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);

  // Initialize WebSocket and audio context
  const connect = async () => {
    try {
      setError("");

      // Get microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 24000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      mediaStreamRef.current = stream;

      // Initialize audio context
      const AudioContextClass = window.AudioContext ||
        (window as typeof window & { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioContext = new AudioContextClass({
        sampleRate: 24000,
      });
      audioContextRef.current = audioContext;

      // Connect to backend WebSocket
      const ws = new WebSocket(
        process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/voice"
      );
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setError("Connection error. Please try again.");
        disconnect();
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
        setIsConnected(false);
        setState("idle");
      };
    } catch (err) {
      console.error("Error connecting:", err);
      setError(
        "Failed to access microphone or connect. Please check permissions."
      );
      disconnect();
    }
  };

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = (message: {
    type: string;
    text?: string;
    data?: string;
    function?: string;
    message?: string;
    [key: string]: unknown;
  }) => {
    switch (message.type) {
      case "ready":
      case "session_ready":
        console.log("Session ready");
        setState("idle");
        startAudioCapture();
        break;

      case "user_started_speaking":
        setState("listening");
        setTranscript("");
        // Stop playing assistant audio
        audioQueueRef.current = [];
        isPlayingRef.current = false;
        setIsAgentSpeaking(false);
        break;

      case "user_stopped_speaking":
        setState("processing");
        break;

      case "assistant_response_started":
        setState("speaking");
        setAssistantText("");
        break;

      case "assistant_response_ended":
        setState("idle");
        break;

      case "audio":
        // Queue audio for playback
        if (message.data) {
          playAudio(message.data);
        }
        break;

      case "user_transcript":
        setTranscript(message.text || "");
        break;

      case "assistant_transcript":
        setAssistantText(message.text || "");
        break;

      case "function_call":
        console.log("Function called:", message.function);
        break;

      case "error":
        console.error("Server error:", message.message);
        setError(message.message || "Unknown error");
        break;

      default:
        console.log("Unknown message type:", message.type);
    }
  };

  // Start audio capture from microphone
  const startAudioCapture = () => {
    if (!audioContextRef.current || !mediaStreamRef.current) return;

    const audioContext = audioContextRef.current;
    const source = audioContext.createMediaStreamSource(mediaStreamRef.current);

    // Use ScriptProcessor for audio capture (compatible with more browsers)
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (e) => {
      if (isMuted || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        return;
      }

      const inputData = e.inputBuffer.getChannelData(0);

      // Convert float32 to PCM16
      const pcm16 = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        const s = Math.max(-1, Math.min(1, inputData[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }

      // Convert to base64 and send
      const base64 = btoa(
        String.fromCharCode.apply(null, Array.from(new Uint8Array(pcm16.buffer)))
      );

      wsRef.current.send(
        JSON.stringify({
          type: "audio",
          data: base64,
        })
      );
    };

    source.connect(processor);
    processor.connect(audioContext.destination);
  };

  // Play audio received from server
  const playAudio = async (base64Audio: string) => {
    if (!audioContextRef.current) return;

    try {
      // Decode base64 to binary
      const binaryString = atob(base64Audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Convert PCM16 to Float32
      const pcm16 = new Int16Array(bytes.buffer);
      const float32 = new Float32Array(pcm16.length);
      for (let i = 0; i < pcm16.length; i++) {
        float32[i] = pcm16[i] / (pcm16[i] < 0 ? 0x8000 : 0x7fff);
      }

      // Create audio buffer
      const audioBuffer = audioContextRef.current.createBuffer(
        1,
        float32.length,
        24000
      );
      audioBuffer.getChannelData(0).set(float32);

      // Queue for playback
      audioQueueRef.current.push(audioBuffer);

      // Mark that agent is speaking
      setIsAgentSpeaking(true);

      // Start playback if not already playing
      if (!isPlayingRef.current) {
        playNextAudio();
      }
    } catch (err) {
      console.error("Error playing audio:", err);
    }
  };

  // Play next audio buffer in queue
  const playNextAudio = () => {
    if (
      audioQueueRef.current.length === 0 ||
      !audioContextRef.current ||
      state === "listening"
    ) {
      isPlayingRef.current = false;
      
      // Notify that audio playback has fully completed
      setIsAgentSpeaking(false);
      console.log("Agent finished speaking - all audio played");
      
      return;
    }

    isPlayingRef.current = true;
    const audioBuffer = audioQueueRef.current.shift()!;

    const source = audioContextRef.current.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContextRef.current.destination);

    source.onended = () => {
      playNextAudio();
    };

    source.start();
  };

  // Disconnect everything
  const disconnect = () => {
    // Stop audio capture
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // Stop microphone
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Clear state
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setIsConnected(false);
    setState("idle");
    setTranscript("");
    setAssistantText("");
    setIsAgentSpeaking(false);
  };

  // Toggle connection
  const toggleConnection = () => {
    if (isConnected) {
      disconnect();
    } else {
      connect();
    }
  };

  // Toggle mute
  const toggleMute = () => {
    setIsMuted(!isMuted);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex flex-col items-center justify-center p-4">
      {/* Header */}
      <div className="absolute top-8 left-1/2 transform -translate-x-1/2 text-center">
        <h1 className="text-4xl font-bold text-white mb-2">
          Voice Assistant
        </h1>
        <p className="text-slate-300">
          Powered by Azure AI Voice Live
        </p>
      </div>

      {/* Main Content */}
      <div className="flex flex-col items-center justify-center space-y-12 max-w-2xl w-full">
        {/* Assistant Orb */}
        <AudioLinesOrb 
          state={!isConnected ? "disconnected" : state}
          isAgentSpeaking={isAgentSpeaking}
        />

        {/* Status Text */}
        <div className="text-center min-h-16">
          {error && (
            <p className="text-red-400 text-lg font-medium">{error}</p>
          )}
          {!error && (
            <>
              {!isConnected && (
                <p className="text-slate-400 text-lg">
                  Click below to start conversation
                </p>
              )}
              {isConnected && state === "idle" && (
                <p className="text-purple-300 text-lg animate-pulse">
                  Listening... Start speaking
                </p>
              )}
              {state === "listening" && (
                <p className="text-blue-300 text-lg font-medium">
                  Listening to you...
                </p>
              )}
              {state === "processing" && (
                <p className="text-yellow-300 text-lg font-medium">
                  Processing...
                </p>
              )}
              {state === "speaking" && (
                <p className="text-green-300 text-lg font-medium">
                  Assistant is speaking...
                </p>
              )}
            </>
          )}
        </div>

        {/* Transcripts */}
        <div className="w-full space-y-4">
          {transcript && (
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-lg p-4 border border-slate-700">
              <p className="text-slate-400 text-sm mb-1">You said:</p>
              <p className="text-white">{transcript}</p>
            </div>
          )}
          {assistantText && (
            <div className="bg-purple-900/30 backdrop-blur-sm rounded-lg p-4 border border-purple-700">
              <p className="text-purple-400 text-sm mb-1">Assistant:</p>
              <p className="text-white">{assistantText}</p>
            </div>
          )}
        </div>

        {/* Control Buttons */}
        <div className="flex gap-4">
          <Button
            size="lg"
            onClick={toggleConnection}
            className={`px-8 py-6 text-lg font-semibold ${
              isConnected
                ? "bg-red-600 hover:bg-red-700"
                : "bg-purple-600 hover:bg-purple-700"
            }`}
          >
            {isConnected ? "Stop Conversation" : "Start Conversation"}
          </Button>

          {isConnected && (
            <Button
              size="lg"
              variant="outline"
              onClick={toggleMute}
              className={`px-6 py-6 ${
                isMuted
                  ? "bg-red-900/50 border-red-700 text-red-300"
                  : "bg-slate-800/50 border-slate-600 text-slate-300"
              }`}
            >
              {isMuted ? (
                <MicOff className="w-6 h-6" />
              ) : (
                <Mic className="w-6 h-6" />
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="absolute bottom-8 text-center text-slate-400 text-sm">
        <p>Try asking about time or weather in your location</p>
      </div>
    </div>
  );
}
