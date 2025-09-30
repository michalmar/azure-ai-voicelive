"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Mic, Square } from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AudioPlaybackQueue, decodeWavToBuffer } from "@/lib/audio";
import { cn } from "@/lib/utils";

const WS_URL = process.env.NEXT_PUBLIC_BACKEND_WS ?? "ws://localhost:8000/ws";
const HTTP_URL = process.env.NEXT_PUBLIC_BACKEND_HTTP ?? "http://localhost:8000";
const TARGET_SAMPLE_RATE = 24000;
const CHUNK_DURATION_MS = 200;
const DEFAULT_SYSTEM_MESSAGE = "Assistant connected. Start speaking.";

type SessionPhase = "idle" | "connecting" | "ready" | "listening" | "processing" | "speaking";

type ConversationMessage = {
  id: string;
  role: "assistant" | "user" | "system";
  text: string;
  transcript?: string | null;
};

type WebSocketMessage = {
  type: string;
  text?: string;
  transcript?: string;
  audio?: string;
  format?: string;
  sampleRate?: number;
  sequence?: number;
  state?: string;
  message?: string;
  function?: string;
  item_id?: string;
  response_id?: string;
};

const stateMap: Record<string, SessionPhase> = {
  ready: "ready",
  listening: "listening",
  processing: "processing",
  speaking: "speaking",
  idle: "ready",
  function_call: "processing",
};

const phaseLabels: Record<SessionPhase, string> = {
  idle: "Ready when you are",
  connecting: "Connecting to Azure...",
  ready: "Standing by",
  listening: "Listening",
  processing: "Thinking",
  speaking: "Speaking",
};

const phasePillStyles: Record<SessionPhase, string> = {
  idle: "bg-slate-300",
  connecting: "bg-amber-400 animate-pulse",
  ready: "bg-emerald-400",
  listening: "bg-sky-500 animate-pulse",
  processing: "bg-amber-500 animate-pulse",
  speaking: "bg-violet-500 animate-pulse",
};

function createId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
}

function downsampleToPCM(
  buffer: Float32Array,
  inputSampleRate: number,
  targetSampleRate: number
): Int16Array {
  if (inputSampleRate === targetSampleRate) {
    const output = new Int16Array(buffer.length);
    for (let i = 0; i < buffer.length; i += 1) {
      const s = Math.max(-1, Math.min(1, buffer[i]));
      output[i] = s * 0x7fff;
    }
    return output;
  }

  const sampleRateRatio = inputSampleRate / targetSampleRate;
  const newLength = Math.floor(buffer.length / sampleRateRatio);
  const result = new Int16Array(newLength);

  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i += 1) {
      accum += buffer[i];
      count += 1;
    }
    const sample = accum / (count || 1);
    result[offsetResult] = Math.max(-1, Math.min(1, sample)) * 0x7fff;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function int16ToBase64(int16: Int16Array): string {
  const bytes = new Uint8Array(int16.buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function AssistantOrb({ phase }: { phase: SessionPhase }) {
  const isSpeaking = phase === "speaking";
  const isListening = phase === "listening";
  const isProcessing = phase === "processing";

  return (
  <div className="relative flex aspect-square w-full max-w-[min(70px,10vw)] items-center justify-center">
      <div
        className={cn(
          "absolute inset-2 rounded-full bg-cyan-200/60 blur-3xl transition-all",
          isSpeaking && "animate-pulseGlow",
          isListening && "opacity-70"
        )}
      />
      <svg
        className={cn("relative h-full w-full", isSpeaking && "animate-spinSlow")}
        viewBox="0 0 200 200"
      >
        <defs>
          <radialGradient id="orbGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.95" />
            <stop offset="70%" stopColor="#2563eb" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0.7" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="8" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle cx="100" cy="100" r="90" fill="url(#orbGradient)" filter="url(#glow)" />
        <circle
          cx="100"
          cy="100"
          r="68"
          fill="none"
          stroke="#e0f2fe"
          strokeWidth="4"
          strokeDasharray="6 4"
          opacity={isListening ? 0.8 : 0.3}
        />
        <circle
          cx="100"
          cy="100"
          r="48"
          fill={isProcessing ? "rgba(255, 255, 255, 0.3)" : "rgba(255, 255, 255, 0.15)"}
          stroke="#bae6fd"
          strokeWidth="2"
          opacity={isSpeaking ? 0.95 : 0.6}
        />
      </svg>
    </div>
  );
}

function useAutoScroll<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  });
  return ref;
}

export default function Home() {
  const [phase, setPhase] = useState<SessionPhase>("idle");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [logOpen, setLogOpen] = useState(true);

  const websocketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | ScriptProcessorNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const playbackQueueRef = useRef<AudioPlaybackQueue | null>(null);
  const floatBufferRef = useRef<Float32Array>(new Float32Array(0));
  const sequenceRef = useRef(0);
  const inputSampleRateRef = useRef(TARGET_SAMPLE_RATE);
  const autoScrollRef = useAutoScroll<HTMLDivElement>();

  const backendInfo = useMemo(
    () => ({
      ws: WS_URL,
      http: HTTP_URL,
    }),
    []
  );

  const handleAssistantTranscript = useCallback((text: string | undefined | null) => {
    if (!text) return;
    setMessages((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i >= 0; i -= 1) {
        if (next[i].role === "assistant") {
          next[i] = { ...next[i], transcript: text };
          return next;
        }
      }
      next.push({ id: createId(), role: "assistant", text, transcript: text });
      return next;
    });
  }, []);

  const handlePCMFrame = useCallback((frame: Float32Array) => {
    const ws = websocketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }

    const chunkSize = Math.floor((inputSampleRateRef.current * CHUNK_DURATION_MS) / 1000);
    const existing = floatBufferRef.current;
    const combined = new Float32Array(existing.length + frame.length);
    combined.set(existing, 0);
    combined.set(frame, existing.length);

    let offset = 0;
    while (combined.length - offset >= chunkSize) {
      const slice = combined.slice(offset, offset + chunkSize);
      const pcm16 = downsampleToPCM(slice, inputSampleRateRef.current, TARGET_SAMPLE_RATE);
      const base64Chunk = int16ToBase64(pcm16);
      sequenceRef.current += 1;
      ws.send(
        JSON.stringify({
          type: "audio_chunk",
          audio: base64Chunk,
          sequence: sequenceRef.current,
          format: "pcm16",
          sampleRate: TARGET_SAMPLE_RATE,
        })
      );
      offset += chunkSize;
    }

    floatBufferRef.current = combined.slice(offset);
  }, []);

  const handleWebSocketMessage = useCallback(
    async (event: MessageEvent) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        switch (data.type) {
          case "assistant_message": {
            const message: ConversationMessage = {
              id: createId(),
              role: "assistant",
              text: data.text ?? "",
              transcript: data.transcript ?? null,
            };
            setMessages((prev) => [...prev, message]);
            setPhase("ready");
            break;
          }
          case "assistant_audio": {
            const context = audioContextRef.current ?? new AudioContext();
            if (!audioContextRef.current) {
              audioContextRef.current = context;
            }
            const playbackQueue = playbackQueueRef.current ?? new AudioPlaybackQueue(context);
            playbackQueueRef.current = playbackQueue;

            if (data.format === "pcm16" && data.audio) {
              playbackQueue.enqueuePCM16(data.audio, data.sampleRate ?? TARGET_SAMPLE_RATE);
            } else if (data.audio && data.format === "wav") {
              const buffer = await decodeWavToBuffer(context, data.audio);
              playbackQueue.enqueueBuffer(buffer);
            }
            setPhase("speaking");
            break;
          }
          case "assistant_transcript": {
            handleAssistantTranscript(data.text);
            break;
          }
          case "assistant_state": {
            const nextPhase = stateMap[data.state ?? ""];
            if (nextPhase) {
              setPhase(nextPhase);
            }
            break;
          }
          case "user_transcript": {
            const userText = data.text ?? "";
            if (userText) {
              setMessages((prev) => [
                ...prev,
                { id: data.item_id ?? createId(), role: "user", text: userText },
              ]);
            }
            break;
          }
          case "system_message": {
            const systemText = data.text ?? "";
            if (systemText) {
              setMessages((prev) => [
                ...prev,
                { id: createId(), role: "system", text: systemText },
              ]);
            }
            break;
          }
          case "error": {
            setError(data.message ?? data.text ?? "An error occurred");
            break;
          }
          case "ack": {
            setPhase("listening");
            break;
          }
          default:
            break;
        }
      } catch (err) {
        console.error("Failed to parse message", err);
      }
    },
    [handleAssistantTranscript]
  );

  const closeSession = useCallback(async () => {
    const ws = websocketRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
    websocketRef.current = null;

    const stream = streamRef.current;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
    streamRef.current = null;

    const worklet = workletNodeRef.current;
    try {
      worklet?.disconnect();
    } catch (err) {
      console.debug("Failed to disconnect worklet", err);
    }
    workletNodeRef.current = null;

    try {
      sourceNodeRef.current?.disconnect();
    } catch (err) {
      console.debug("Failed to disconnect source node", err);
    }
    sourceNodeRef.current = null;

    const context = audioContextRef.current;
    if (context) {
      try {
        await context.close();
      } catch (err) {
        console.debug("AudioContext close failed", err);
      }
    }
    audioContextRef.current = null;
    playbackQueueRef.current = null;
    floatBufferRef.current = new Float32Array(0);
    inputSampleRateRef.current = TARGET_SAMPLE_RATE;
    sequenceRef.current = 0;

    setIsActive(false);
    setPhase("idle");
  }, []);

  const startSession = useCallback(async () => {
    setError(null);
    setPhase("connecting");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const ws = new WebSocket(backendInfo.ws);
      ws.onmessage = (evt) => {
        void (async () => {
          await handleWebSocketMessage(evt);
        })();
      };
      ws.onerror = () => {
        setError("Unable to connect to assistant backend.");
        void closeSession();
      };
      ws.onopen = () => {
        setPhase("ready");
        setIsActive(true);
      };
      ws.onclose = () => {
        void closeSession();
      };

      websocketRef.current = ws;
      streamRef.current = stream;

      const context = new AudioContext();
      audioContextRef.current = context;
      inputSampleRateRef.current = context.sampleRate;
      await context.audioWorklet?.addModule?.("/worklets/pcm-processor.js");

      const source = context.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      if (context.audioWorklet) {
        const node = new AudioWorkletNode(context, "pcm-processor");
        workletNodeRef.current = node;
        node.port.onmessage = (evt) => {
          handlePCMFrame(evt.data as Float32Array);
        };
        source.connect(node);
      } else {
        const processor = context.createScriptProcessor(2048, 1, 1);
        workletNodeRef.current = processor;
        processor.onaudioprocess = (evt) => {
          const channelData = evt.inputBuffer.getChannelData(0);
          handlePCMFrame(channelData.slice());
        };
        source.connect(processor);
        processor.connect(context.destination);
      }

      await context.resume();
      playbackQueueRef.current = new AudioPlaybackQueue(context);
      floatBufferRef.current = new Float32Array(0);
      sequenceRef.current = 0;
      setMessages([
        { id: createId(), role: "system", text: DEFAULT_SYSTEM_MESSAGE },
      ]);
    } catch (err) {
      console.error(err);
      setError("Microphone permissions are required to start the session.");
      await closeSession();
    }
  }, [backendInfo.ws, closeSession, handlePCMFrame, handleWebSocketMessage]);

  const stopSession = useCallback(async () => {
    const ws = websocketRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "stop" }));
    }
    await closeSession();
  }, [closeSession]);

  const toggleSession = useCallback(() => {
    if (isActive || websocketRef.current) {
      void stopSession();
    } else {
      void startSession();
    }
  }, [isActive, startSession, stopSession]);

  useEffect(() => {
    return () => {
      void closeSession();
    };
  }, [closeSession]);

  const buttonLabel = !isActive
    ? phase === "connecting"
      ? "Connecting..."
      : "Start Conversation"
    : "Stop Conversation";

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-100 via-white to-slate-200">
      <div className="container mx-auto max-w-5xl space-y-8 px-4 py-16">
        <Card className="border-none bg-white/70 shadow-xl backdrop-blur">
          <CardHeader className="items-center text-center space-y-3">
            <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-700">
              Azure Voice Live • Preview
            </span>
            <CardTitle className="text-3xl font-semibold">Personal Voice Companion</CardTitle>
            <CardDescription className="text-base">
              Stream your voice to Azure Voice Live and hear natural responses in real time. No clicks needed—just talk.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="grid gap-10 md:grid-cols-[minmax(0,1fr)_minmax(220px,0.4fr)] md:items-center">
              <div className="flex flex-col items-center gap-6 text-center md:items-start md:text-left">
                <div className="flex items-center gap-3 rounded-lg bg-white/80 px-4 py-2 shadow-sm">
                  <span className={cn("h-2.5 w-2.5 rounded-full", phasePillStyles[phase])} />
                  <p className="text-sm font-medium text-slate-700">{phaseLabels[phase]}</p>
                </div>
                <p className="max-w-xl text-sm text-muted-foreground">
                  The assistant continuously listens while the session is active. Stop anytime to end the stream and reset the context.
                </p>
                <div className="flex flex-col items-center gap-3 md:flex-row md:items-center">
                  <Button
                    onClick={toggleSession}
                    disabled={phase === "connecting"}
                    className={cn(buttonVariants({ size: "lg" }), "gap-2")}
                  >
                    {isActive ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                    {buttonLabel}
                  </Button>
                  {error ? (
                    <p className="text-sm text-red-500 md:text-left">{error}</p>
                  ) : (
                    <p className="text-xs text-muted-foreground md:text-left">
                      Tip: grant microphone access when prompted.
                    </p>
                  )}
                </div>
              </div>
              <div className="flex justify-center md:justify-end">
                <AssistantOrb phase={phase} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-none bg-white/65 shadow-lg backdrop-blur">
          <CardHeader className="flex flex-row items-center justify-between gap-4">
            <div className="space-y-1.5">
              <CardTitle className="text-xl font-semibold">Conversation log</CardTitle>
              <CardDescription>Review what you and the assistant said, including running transcripts.</CardDescription>
            </div>
            <Button
              onClick={() => setLogOpen((prev) => !prev)}
              aria-expanded={logOpen}
              aria-controls="conversation-log"
              className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "text-slate-500")}
            >
              {logOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              <span className="sr-only">Toggle conversation log visibility</span>
            </Button>
          </CardHeader>
          {logOpen ? (
            <CardContent className="pt-0" id="conversation-log">
              <div
                ref={autoScrollRef}
                className="flex max-h-80 flex-col gap-3 overflow-y-auto rounded-xl bg-white/70 p-4 shadow-inner"
              >
                {messages.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No messages yet. Start the session to see the conversation unfold.
                  </p>
                ) : (
                  messages.map((msg) => {
                    const isUser = msg.role === "user";
                    const isSystem = msg.role === "system";
                    const bubbleClasses = isSystem
                      ? "self-center max-w-md rounded-full bg-slate-100/80 px-4 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground"
                      : isUser
                      ? "self-end max-w-xs rounded-3xl bg-sky-500 px-4 py-3 text-sm text-white shadow-lg"
                      : "self-start max-w-xs rounded-3xl bg-white px-4 py-3 text-sm text-slate-800 shadow";

                    return (
                      <article key={msg.id} className={bubbleClasses}>
                        <p>{msg.text}</p>
                        {msg.transcript && !isSystem ? (
                          <p className="mt-2 text-xs uppercase tracking-wide text-sky-700/80">
                            Transcript: {msg.transcript}
                          </p>
                        ) : null}
                      </article>
                    );
                  })
                )}
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Backend: <span className="font-semibold">{backendInfo.http}</span> · WebSocket: {backendInfo.ws}
              </p>
            </CardContent>
          ) : null}
        </Card>
      </div>
    </main>
  );
}
