"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Globe } from "lucide-react";

export interface Locale {
  id: string;
  name: string;
  flag: string;
  description: string;
}

interface LocaleSelectorProps {
  selectedLocale: string;
  onLocaleChange: (localeId: string) => void;
  disabled?: boolean;
}

export default function LocaleSelector({
  selectedLocale,
  onLocaleChange,
  disabled = false,
}: LocaleSelectorProps) {
  const [locales, setLocales] = useState<Locale[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchLocales = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${apiUrl}/locales`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setLocales(data.locales);
        if (!selectedLocale && data.default) {
          onLocaleChange(data.default);
        }
      } catch (error) {
        console.error("Failed to fetch locales:", error);
        setLocales([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchLocales();
  }, []);

  const selectedLocaleData = locales.find((l) => l.id === selectedLocale);

  const handleSelect = (localeId: string) => {
    onLocaleChange(localeId);
    setIsOpen(false);
  };

  if (isLoading) {
    return (
      <div className="w-48 h-14 bg-slate-800/50 rounded-lg animate-pulse border border-slate-700" />
    );
  }

  return (
    <div className="relative w-48">
      <button
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`w-full flex items-center justify-between gap-3 px-4 py-3 rounded-lg border transition-all ${
          disabled
            ? "bg-slate-800/30 border-slate-700/50 cursor-not-allowed opacity-60"
            : "bg-slate-800/50 border-slate-700 hover:border-blue-500 hover:bg-slate-800/70 cursor-pointer"
        }`}
      >
        <div className="flex items-center gap-3">
          <div className="text-2xl">
            {selectedLocaleData?.flag || "🌐"}
          </div>
          <div className="text-left">
            <p className="text-white font-medium text-sm">
              {selectedLocaleData?.name || "Select Language"}
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
                <Globe className="w-4 h-4 text-blue-400" />
                <span className="text-xs text-slate-400 uppercase tracking-wide">
                  Language
                </span>
              </div>
            </div>
            <div className="py-1 max-h-60 overflow-y-auto">
              {locales.map((locale) => (
                <button
                  key={locale.id}
                  onClick={() => handleSelect(locale.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-700/50 transition-colors ${
                    selectedLocale === locale.id ? "bg-blue-900/30" : ""
                  }`}
                >
                  <div className="text-2xl">
                    {locale.flag}
                  </div>
                  <div className="text-left flex-1">
                    <p
                      className={`font-medium text-sm ${
                        selectedLocale === locale.id
                          ? "text-blue-300"
                          : "text-white"
                      }`}
                    >
                      {locale.name}
                    </p>
                    <p className="text-slate-400 text-xs">{locale.description}</p>
                  </div>
                  {selectedLocale === locale.id && (
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
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
