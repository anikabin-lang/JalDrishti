import React from 'react';
import { useLanguage } from '../i18n/LanguageContext';

export const LanguageSelector: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { language, setLanguage, languages, t } = useLanguage();

  return (
    <div className={`relative inline-flex items-center ${className}`}>
      <label htmlFor="language-select" className="sr-only">
        {t('header.language')}
      </label>
      <div className="flex items-center gap-1.5 rounded-full border border-ws-border bg-ws-card px-2.5 py-1 text-xs text-ws-text transition hover:border-ws-jade-light/40">
        <span className="text-sm" aria-hidden="true">🌐</span>
        <select
          id="language-select"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="cursor-pointer bg-transparent font-medium text-ws-text focus:outline-none"
        >
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code} className="bg-ws-card text-ws-text">
              {lang.nativeName} ({lang.name})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

