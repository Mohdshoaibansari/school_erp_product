import { useEffect, useState } from 'react';
import { AppShell as MantineAppShell } from '@mantine/core';
import { Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

/**
 * Persistent sidebar at >= 1024px (md breakpoint overridden to 64em),
 * off-canvas drawer below (REQ-SHELL-04, P1-AC-2).
 */
export function AppShell() {
  const [opened, setOpened] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setOpened(false);
  }, [location.pathname]);

  return (
    <MantineAppShell
      header={{ height: 60 }}
      navbar={{ width: 240, breakpoint: 'md', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <MantineAppShell.Header>
        <Header onMenuToggle={() => setOpened((o) => !o)} />
      </MantineAppShell.Header>
      <MantineAppShell.Navbar>
        <Sidebar onNavigate={() => setOpened(false)} />
      </MantineAppShell.Navbar>
      <MantineAppShell.Main>
        <Outlet />
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}
