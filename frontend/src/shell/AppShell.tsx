import { useEffect, useState } from 'react';
import { AppShell as MantineAppShell } from '@mantine/core';
import { Outlet, useLocation } from 'react-router-dom';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

const COLLAPSE_KEY = 'sidebar-collapsed';

export function AppShell() {
  const [opened, setOpened] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(COLLAPSE_KEY) === 'true'; } catch { return false; }
  });
  const location = useLocation();
  useEffect(() => setOpened(false), [location.pathname]);
  useEffect(() => { try { localStorage.setItem(COLLAPSE_KEY, String(collapsed)); } catch {} }, [collapsed]);

  const sidebarWidth = collapsed ? 78 : 258;
  return (
    <MantineAppShell
      header={{ height: 76 }}
      navbar={{ width: sidebarWidth, breakpoint: 'md', collapsed: { mobile: !opened } }}
      padding={{ base: 'md', md: 'xl' }}
    >
      <MantineAppShell.Header style={{ background: 'rgba(250,250,250,.86)', backdropFilter: 'blur(18px)', borderBottom: '1px solid #E2E8F0' }}>
        <Header onMenuToggle={() => setOpened((o) => !o)} />
      </MantineAppShell.Header>
      <MantineAppShell.Navbar style={{ background: '#0F172A', border: 0 }}>
        <Sidebar onNavigate={() => setOpened(false)} collapsed={collapsed} onToggleCollapse={() => setCollapsed((c) => !c)} />
      </MantineAppShell.Navbar>
      <MantineAppShell.Main>
        <ErrorBoundary><Outlet /></ErrorBoundary>
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}
