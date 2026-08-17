import { useEffect, useState } from 'react';
import { AppShell as MantineAppShell } from '@mantine/core';
import { Outlet, useLocation } from 'react-router-dom';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

const COLLAPSE_KEY = 'sidebar-collapsed';

/**
 * Persistent sidebar at >= 1024px (md breakpoint overridden to 64em),
 * off-canvas drawer below (REQ-SHELL-04, P1-AC-2).
 */
export function AppShell() {
  const [opened, setOpened] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === 'true';
    } catch {
      return false;
    }
  });
  const location = useLocation();

  useEffect(() => {
    setOpened(false);
  }, [location.pathname]);

  useEffect(() => {
    try {
      localStorage.setItem(COLLAPSE_KEY, String(collapsed));
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  const sidebarWidth = collapsed ? 72 : 240;

  return (
    <MantineAppShell
      header={{ height: 60 }}
      navbar={{ width: sidebarWidth, breakpoint: 'md', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <MantineAppShell.Header>
        <Header onMenuToggle={() => setOpened((o) => !o)} />
      </MantineAppShell.Header>
      <MantineAppShell.Navbar>
        <Sidebar
          onNavigate={() => setOpened(false)}
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((c) => !c)}
        />
      </MantineAppShell.Navbar>
      <MantineAppShell.Main>
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}
