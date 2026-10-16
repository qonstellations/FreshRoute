import {
  ActionIcon, AppShell, Group, Text, Tooltip, useMantineColorScheme
} from '@mantine/core'
import {
  IconArrowLeft, IconArrowRight, IconLeaf, IconMoon, IconSun
} from '@tabler/icons-react'
import { lazy, Suspense, useEffect, useState } from 'react'
import { flushSync } from 'react-dom'
import { CustomCursor } from './components/CustomCursor'
import { LandingPage } from './pages/LandingPage'

// Dashboard pulls recharts + all tabs; keep it off the landing page's critical path.
const loadDashboard = () => import('./pages/Dashboard')
const Dashboard = lazy(() => loadDashboard().then((m) => ({ default: m.Dashboard })))

// The view transition holds the old frame until `sel` renders (or `ms` passes), so the morph lands on a
// drawn dashboard rather than a skeleton. ponytail: rAF poll; a MutationObserver is the upgrade if this ever shows in a profile.
function waitFor(sel: string, ms: number) {
  const end = performance.now() + ms
  return new Promise<void>((done) => {
    const tick = () => (document.querySelector(sel) || performance.now() > end ? done() : requestAnimationFrame(tick))
    tick()
  })
}

export default function App() {
  const [view, setView] = useState<'landing' | 'dashboard'>(() => {
    return window.location.hash.includes('dashboard') ? 'dashboard' : 'landing'
  })

  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem('fr-theme') === 'dark'
    } catch {
      return false
    }
  })

  const { setColorScheme } = useMantineColorScheme()

  useEffect(() => {
    setColorScheme(dark ? 'dark' : 'light')
    try {
      localStorage.setItem('fr-theme', dark ? 'dark' : 'light')
    } catch {
      /* private browsing */
    }
  }, [dark, setColorScheme])

  useEffect(() => {
    const onHashChange = () => {
      setView(window.location.hash.includes('dashboard') ? 'dashboard' : 'landing')
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  // warm the dashboard chunk once the landing page is idle, so the launch morph rarely waits on the network
  useEffect(() => {
    const t = setTimeout(() => { loadDashboard().catch(() => {}) }, 1500)
    return () => clearTimeout(t)
  }, [])

  // launched from the landing page = opens on today's plan
  const [entryTab, setEntryTab] = useState<string | undefined>(undefined)

  // Landing <-> dashboard as one view transition: the clicked control grows into the dashboard header (CSS in
  // index.css). Without support it is a plain cut.
  const switchView = (target: 'landing' | 'dashboard', from?: HTMLElement) => {
    const apply = () => {
      flushSync(() => {
        setEntryTab(target === 'dashboard' ? 'trucks' : undefined)
        setView(target)
      })
      window.location.hash = target === 'dashboard' ? '/dashboard' : '/'
      window.scrollTo(0, 0)
    }
    if (!document.startViewTransition || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return apply()
    if (from) from.style.viewTransitionName = 'launch'
    const vt = document.startViewTransition(async () => {
      apply()
      if (target === 'dashboard') await waitFor('.plan-map', 900)
    })
    vt.ready.catch(() => {}) // a skipped transition (tab hidden, clicked again) is a plain cut, not an error
  }

  return (
    <>
      <CustomCursor />
      <AppShell header={{ height: 60 }} padding={0}>
        <AppShell.Header className="atelier-header">
          <Group h="100%" px="lg" justify="space-between">
            {/* Logo & Wordmark */}
            <Group
              gap={8}
              style={{ cursor: 'pointer' }}
              onClick={() => switchView('landing')}
              data-cursor="HOME"
            >
              <IconLeaf size={24} color="var(--ink)" stroke={2.2} />
              <Text className="wordmark-sm" fz={20}>
                FRESHROUTE
              </Text>
            </Group>

            {view === 'dashboard' && (
              <Group gap={8}>
                <button
                  className="atelier-ghost"
                  onClick={() => switchView('landing')}
                  style={{ padding: '6px 14px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6 }}
                  data-cursor="BACK"
                >
                  <IconArrowLeft size={14} />
                  <span>BACK TO OVERVIEW</span>
                </button>
              </Group>
            )}

            {/* Right Header Actions */}
            <Group gap="sm">
              {view === 'landing' && (
                <button
                  className="atelier-cta"
                  onClick={(e) => switchView('dashboard', e.currentTarget)}
                  style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                  data-cursor="CONSOLE"
                >
                  <span className="cta-mask">
                    <span className="cta-label">OPEN LIVE DEMO</span>
                    <span className="cta-clone">OPEN LIVE DEMO</span>
                  </span>
                  <span className="cta-div" aria-hidden />
                  <IconArrowRight size={14} />
                </button>
              )}

              <Tooltip label={dark ? 'Light mode' : 'Dark mode'}>
                <ActionIcon
                  variant="subtle"
                  size="lg"
                  aria-label="Toggle theme"
                  onClick={() => setDark((v) => !v)}
                  data-cursor="THEME"
                >
                  {dark ? <IconSun size={20} /> : <IconMoon size={20} />}
                </ActionIcon>
              </Tooltip>
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Main>
          {view === 'landing' ? (
            <LandingPage onLaunch={(from) => switchView('dashboard', from)} />
          ) : (
            <Suspense fallback={<Text p="xl">Loading…</Text>}>
              <Dashboard onBackToOverview={() => switchView('landing')} initialTab={entryTab} />
            </Suspense>
          )}
        </AppShell.Main>
      </AppShell>
    </>
  )
}
