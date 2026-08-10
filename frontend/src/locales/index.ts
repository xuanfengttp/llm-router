import { useAppStore } from '@/store/appStore';
import en from './en';
import zh from './zh';

/**
 * 轻量 i18n：
 * - key 就是中文原文（"控制台"、"设置" 等）
 * - 中文模式：直接返回 key 本身
 * - 英文模式：查英文字典
 * - 未找到时：fallback 到 key 本身
 */
export function translate(key: string, language?: string): string {
  const lang = language ?? 'zh';
  if (lang === 'zh') {
    // 中文模式下有特殊覆盖的用 zh 字典，否则原样返回 key
    return zh[key] ?? key;
  }
  // 英文模式：查字典
  return en[key] ?? key;
}

/** 带插值替换，如 "确定删除 Provider "{}" 及其所有模型？" -> format args */
export function tfmt(key: string, ...args: (string | number)[]): string {
  const lang = useAppStore.getState().settings?.language ?? 'zh';
  let result = translate(key, lang);
  args.forEach((arg) => {
    result = result.replace('{}', String(arg));
  });
  return result;
}

/** React Hook: 订阅语言设置，返回翻译函数 */
export function useT() {
  const language = useAppStore((s) => s.settings.language ?? 'zh');
  return (key: string) => translate(key, language);
}

/** React Hook: 带格式化插值的翻译 */
export function useTf() {
  const language = useAppStore((s) => s.settings.language ?? 'zh');
  return (key: string, ...args: (string | number)[]) => {
    let result = translate(key, language);
    args.forEach((arg) => {
      result = result.replace('{}', String(arg));
    });
    return result;
  };
}
