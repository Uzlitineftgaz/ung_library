import {Injectable} from '@angular/core';
import {Translation, TranslocoLoader} from '@jsverse/transloco';
import {from, of, Observable} from 'rxjs';
import en from '../../../i18n/en';

export const EN_TRANSLATIONS: Translation = en;

// To add a new language: create src/i18n/<lang>/ with domain JSONs + index.ts, then add an entry here.
const LAZY_LANG_LOADERS: Record<string, () => Promise<{default: Translation}>> = {
  ru: () => import('../../../i18n/ru'),
  uz: () => import('../../../i18n/uz'),
};

export const AVAILABLE_LANGS = ['en', 'ru', 'uz'];

export const LANG_LABELS: Record<string, string> = {
  en: 'English',
  ru: 'Русский',
  uz: "O'zbekcha",
};

function deepMerge(base: Record<string, any>, override: Record<string, any>): Record<string, any> {
  const result = {...base};
  for (const key of Object.keys(override)) {
    if (override[key] && typeof override[key] === 'object' && !Array.isArray(override[key])
      && base[key] && typeof base[key] === 'object' && !Array.isArray(base[key])) {
      result[key] = deepMerge(base[key], override[key]);
    } else if (override[key] !== '') {
      result[key] = override[key];
    }
  }
  return result;
}

@Injectable({providedIn: 'root'})
export class TranslocoInlineLoader implements TranslocoLoader {
  getTranslation(lang: string): Observable<Translation> {
    if (lang === 'en') {
      return of(EN_TRANSLATIONS);
    }
    const loader = LAZY_LANG_LOADERS[lang];
    if (loader) {
      return from(loader().then(m => deepMerge(EN_TRANSLATIONS, m.default)));
    }
    return of(EN_TRANSLATIONS);
  }
}
