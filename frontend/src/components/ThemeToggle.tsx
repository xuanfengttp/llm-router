import { useAppStore } from '@/store/appStore';
import { Sun, Moon } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);

  return (
    <Button variant="ghost" size="icon" onClick={toggleTheme} title="Toggle theme">
      {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </Button>
  );
}
