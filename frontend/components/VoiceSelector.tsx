"use client";

import { useEffect, useState } from "react";
import { ChevronDown, User, Mic2 } from "lucide-react";

export interface Voice {
  id: string;
  name: string;
  voice: string;
  locale: string;
  description: string;
}

interface VoiceSelectorProps {
  selectedVoice: string;
  onVoiceChange: (voiceId: string) => void;
  selectedLocale: string;
  disabled?: boolean;
}

export default function VoiceSelector({
  selectedVoice,
  onVoiceChange,
  selectedLocale,
  disabled = false,
}: VoiceSelectorProps) {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchVoices = async () => {
      setIsLoading(true);
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${apiUrl}/voices?locale=${selectedLocale}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setVoices(data.voices);
        // Auto-select the default voice for this locale
        if (data.default) {
          onVoiceChange(data.default);
        }
      } catch (error) {
        console.error("Failed to fetch voices:", error);
        setVoices([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchVoices();
  }, [selectedLocale]);

  const selectedVoiceData = voices.find((v) => v.id === selectedVoice);

  const handleSelect = (voiceId: string) => {
    onVoiceChange(voiceId);
    setIsOpen(false);
  };

  if (isLoading) {
    return (
      <div className="w-64 h-14 bg-slate-800/50 rounded-lg animate-pulse border border-slate-700" />
    );
  }

  return (
    <div className="relative w-64">
      <button
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`w-full flex items-center justify-between gap-3 px-4 py-3 rounded-lg border transition-all ${
          disabled
            ? "bg-slate-800/30 border-slate-700/50 cursor-not-allowed opacity-60"
            : "bg-slate-800/50 border-slate-700 hover:border-purple-500 hover:bg-slate-800/70 cursor-pointer"
        }`}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-purple-600/30 flex items-center justify-center">
            <User className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-left">
            <p className="text-white font-medium text-sm">
              {selectedVoiceData?.name || "Select Voice"}
            </p>
            <p className="text-slate-400 text-xs">
              {selectedVoiceData?.description || "Choose assistant voice"}
            </p>
          </div>
        </div>
        <ChevronDown
          className={`w-5 h-5 text-slate-400 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {isOpen && !disabled && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown */}
          <div className="absolute top-full left-0 right-0 mt-2 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-20 overflow-hidden">
            <div className="p-2 border-b border-slate-700">
              <div className="flex items-center gap-2 px-2 py-1">
                <Mic2 className="w-4 h-4 text-purple-400" />
                <span className="text-xs text-slate-400 uppercase tracking-wide">
                  Available Voices
                </span>
              </div>
            </div>
            <div className="py-1 max-h-60 overflow-y-auto">
              {voices.map((voice) => (
                <button
                  key={voice.id}
                  onClick={() => handleSelect(voice.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-700/50 transition-colors ${
                    selectedVoice === voice.id ? "bg-purple-900/30" : ""
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      selectedVoice === voice.id
                        ? "bg-purple-600"
                        : "bg-slate-700"
                    }`}
                  >
                    <User
                      className={`w-4 h-4 ${
                        selectedVoice === voice.id
                          ? "text-white"
                          : "text-slate-400"
                      }`}
                    />
                  </div>
                  <div className="text-left flex-1">
                    <p
                      className={`font-medium text-sm ${
                        selectedVoice === voice.id
                          ? "text-purple-300"
                          : "text-white"
                      }`}
                    >
                      {voice.name}
                    </p>
                    <p className="text-slate-400 text-xs">{voice.description}</p>
                  </div>
                  {selectedVoice === voice.id && (
                    <div className="w-2 h-2 rounded-full bg-purple-500" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
