import {
  ActionIcon, AppShell, Group, Text, Tooltip, useMantineColorScheme
} from '@mantine/core'
import {
  IconArrowLeft, IconArrowRight, IconLeaf, IconMoon, IconSun
} from '@tabler/icons-react'
import { gsap } from 'gsap'
import { useEffect, useState } from 'react'
import { CustomCursor } from './components/CustomCursor'
import { Dashboard } from './pages/Dashboard'
import { LandingPage } from './pages/LandingPage'

const NAV_SECTIONS = [
  { id: 'crisis', n: '01', label: 'CRISIS' },
  { id: 'workflow', n: '02', label: 'WORKFLOW' },
  { id: 'results', n: '03', label: 'BENCHMARK' },
  { id: 'audit', n: '04', label: 'TRUST' },
]

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

  const switchView = (target: 'landing' | 'dashboard') => {
    setView(target)
    window.location.hash = target === 'dashboard' ? '/dashboard' : '/'
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const scrollToAnchor = (id: string) => {
    if (view !== 'landing') {
      switchView('landing')
      setTimeout(() => {
        gsap.to(window, { duration: 1, ease: 'power3.inOut', scrollTo: { y: `#${id}`, offsetY: 70 } })
      }, 100)
    } else {
      gsap.to(window, { duration: 1, ease: 'power3.inOut', scrollTo: { y: `#${id}`, offsetY: 70 } })
    }
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

            {/* Landing Navigation: Section scroll links */}
            {view === 'landing' ? (
              <Group gap={6} visibleFrom="md" className="landing-nav-links">
                {NAV_SECTIONS.map((sec) => (
                  <button
                    key={sec.id}
                    className="landing-nav-link"
                    onClick={() => scrollToAnchor(sec.id)}
                    data-cursor="GO"
                  >
                    <span style={{ opacity: 0.65, marginRight: 4 }}>[{sec.n}]</span>
                    {sec.label}
                  </button>
                ))}
              </Group>
            ) : (
              <Group gap={8}>
                <button
                  className="atelier-ghost"
                  onClick={() => switchView('landing')}
                  style={{ padding: '6px 14px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6 }}
                  data-cursor="BACK"
                >
                  <IconArrowLeft size={14} />
                  <span>BACK TO PRODUCT STORY</span>
                </button>
              </Group>
            )}

            {/* Right Header Actions */}
            <Group gap="sm">
              {view === 'landing' && (
                <button
                  className="atelier-cta"
                  onClick={() => switchView('dashboard')}
                  style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                  data-cursor="CONSOLE"
                >
                  <span className="cta-mask">
                    <span className="cta-label">LAUNCH CONSOLE</span>
                    <span className="cta-clone">LAUNCH CONSOLE</span>
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
            <LandingPage onLaunch={() => switchView('dashboard')} />
          ) : (
            <Dashboard onBackToStory={() => switchView('landing')} />
          )}
        </AppShell.Main>
      </AppShell>
    </>
  )
}
