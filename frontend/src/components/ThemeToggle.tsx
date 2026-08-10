import { useAppStore } from '@/store/appStore';
import { Sun, Moon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useT } from '@/locales';

export function ThemeToggle() {
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const t = useT();

  return (
    <Button variant="ghost" size="icon" onClick={toggleTheme} title={t('切换主题')}>
      {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </Button>
  );
}
