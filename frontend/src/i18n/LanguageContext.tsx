import React, { createContext, useContext, useEffect, useState } from 'react';
import { SUPPORTED_LANGUAGES, TRANSLATIONS, LanguageOption } from './translations';
import { getBaseUrl } from '../services/api';

interface LanguageContextType {
  language: string;
  setLanguage: (lang: string) => Promise<void>;
  t: (key: string, fallback?: string) => string;
  isRtl: boolean;
  currentOption: LanguageOption;
  languages: LanguageOption[];
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<string>(() => {
    return localStorage.getItem('jaldrishti_language') || 'en';
  });

  const currentOption =
    SUPPORTED_LANGUAGES.find((l) => l.code === language) || SUPPORTED_LANGUAGES[0];
  const isRtl = Boolean(currentOption.isRtl);

  // Sync RTL and lang attribute on document root
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
  }, [language, isRtl]);

  // Try fetching user preference from backend on mount
  useEffect(() => {
    const fetchPref = async () => {
      try {
        const base = getBaseUrl();
        const res = await fetch(`${base}/preferences/language`);
        if (res.ok) {
          const data = await res.json();
          if (data.language && data.language !== language) {
            setLanguageState(data.language);
            localStorage.setItem('jaldrishti_language', data.language);
          }
        }
      } catch {
        // Fallback to local state if backend unreachable
      }
    };
    fetchPref();
  }, []);

  const setLanguage = async (newLang: string) => {
    setLanguageState(newLang);
    localStorage.setItem('jaldrishti_language', newLang);
    try {
      const base = getBaseUrl();
      await fetch(`${base}/preferences/language`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: newLang }),
      });
    } catch {
      // Preference saved locally even if network fails
    }
  };

  const t = (key: string, fallback?: string): string => {
    const dict = TRANSLATIONS[language] || TRANSLATIONS['en'] || {};
    const val = dict[key] || TRANSLATIONS['en']?.[key];
    if (val !== undefined) return val;
    return fallback !== undefined ? fallback : key;
  };

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        t,
        isRtl,
        currentOption,
        languages: SUPPORTED_LANGUAGES,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

