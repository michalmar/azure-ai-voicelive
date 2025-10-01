"use client";

import { useEffect, useState } from "react";

type OrbState = "idle" | "listening" | "processing" | "speaking" | "disconnected";

interface AudioLinesOrbProps {
  state: OrbState;
}

export default function AudioLinesOrb({ state }: AudioLinesOrbProps) {
  const [lineLengths, setLineLengths] = useState<number[]>([]);

  // Initialize line heights
  useEffect(() => {
    setLineLengths([0.3, 0.5, 0.8, 0.4, 0.7, 0.5, 0.2]);
  }, []);

  // Animate lines when speaking
  useEffect(() => {
    if (state === "speaking") {
      const interval = setInterval(() => {
        setLineLengths((prev) =>
          prev.map(() => Math.random() * 0.7 + 0.3)
        );
      }, 100);

      return () => clearInterval(interval);
    } else if (state === "listening") {
      // Gentle wave animation for listening
      const interval = setInterval(() => {
        setLineLengths((prev) =>
          prev.map((_, i) => {
            const phase = (Date.now() / 500 + i * 0.3) % (Math.PI * 2);
            return 0.4 + Math.sin(phase) * 0.3;
          })
        );
      }, 50);

      return () => clearInterval(interval);
    } else if (state === "processing") {
      // Slow wave for processing
      const interval = setInterval(() => {
        setLineLengths((prev) =>
          prev.map((_, i) => {
            const phase = (Date.now() / 800 + i * 0.5) % (Math.PI * 2);
            return 0.5 + Math.sin(phase) * 0.2;
          })
        );
      }, 50);

      return () => clearInterval(interval);
    } else {
      // Reset to idle positions
      setLineLengths([0.3, 0.5, 0.8, 0.4, 0.7, 0.5, 0.2]);
    }
  }, [state]);

  // Determine colors and glow based on state
  const getStateColors = () => {
    switch (state) {
      case "idle":
        return {
          line: "bg-purple-400",
          glow: "shadow-purple-500/50",
          outerGlow: "bg-purple-500",
        };
      case "listening":
        return {
          line: "bg-blue-400",
          glow: "shadow-blue-500/50",
          outerGlow: "bg-blue-500",
        };
      case "processing":
        return {
          line: "bg-yellow-400",
          glow: "shadow-yellow-500/50",
          outerGlow: "bg-yellow-500",
        };
      case "speaking":
        return {
          line: "bg-green-400",
          glow: "shadow-green-500/50",
          outerGlow: "bg-green-500",
        };
      case "disconnected":
        return {
          line: "bg-slate-600",
          glow: "shadow-slate-600/50",
          outerGlow: "bg-slate-600",
        };
      default:
        return {
          line: "bg-purple-400",
          glow: "shadow-purple-500/50",
          outerGlow: "bg-purple-500",
        };
    }
  };

  const colors = getStateColors();

  return (
    <div className="relative flex items-center justify-center">
      {/* Outer glow effects based on state */}
      {state === "idle" && (
        <div className="absolute inset-0 animate-pulse-glow">
          <div className="w-48 h-48 rounded-full bg-purple-500 opacity-20 blur-3xl" />
        </div>
      )}

      {state === "listening" && (
        <>
          <div className="absolute inset-0 animate-pulse-fast">
            <div className="w-48 h-48 rounded-full bg-blue-500 opacity-30 blur-3xl" />
          </div>
          <div className="absolute inset-0 animate-ping">
            <div className="w-48 h-48 rounded-full bg-blue-400 opacity-20" />
          </div>
        </>
      )}

      {state === "processing" && (
        <div className="absolute inset-0 animate-spin-slow">
          <div className="w-48 h-48 rounded-full bg-gradient-to-r from-yellow-400 to-orange-400 opacity-20 blur-2xl" />
        </div>
      )}

      {state === "speaking" && (
        <>
          <div className="absolute inset-0 animate-spin-slow">
            <div className="w-60 h-60 rounded-full bg-gradient-to-r from-green-400 via-emerald-400 to-teal-400 opacity-40 blur-3xl" />
          </div>
          <div className="absolute inset-0 animate-pulse-fast">
            <div className="w-52 h-52 rounded-full bg-green-400 opacity-30 blur-2xl" />
          </div>
        </>
      )}

      {/* Audio lines container */}
      <div className="relative z-10 flex items-center justify-center gap-2 h-48 w-48">
        <div className="flex items-center justify-center gap-3 h-32">
          {lineLengths.map((length, index) => (
            <div
              key={index}
              className={`w-4 rounded-full ${colors.line} shadow-lg ${colors.glow} transition-all duration-100 ease-out`}
              style={{
                height: `${length * 100}%`,
                minHeight: "12px",
              }}
            />
          ))}
        </div>
      </div>

      {/* Additional pulsing effect for speaking */}
      {state === "speaking" && (
        <div className="absolute inset-0 animate-pulse-glow pointer-events-none">
          <div className="w-full h-full rounded-full bg-green-400/10 blur-xl" />
        </div>
      )}
    </div>
  );
}
