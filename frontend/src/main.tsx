import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter'
import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'
import { MantineProvider } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import { LazyMotion, MotionConfig, domMax } from 'motion/react'
import App from './App'
import { theme } from './theme'
import './index.css'

// D-24: Mantine for components, motion for spring animations (reduced motion honoured).
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="light">
      <LazyMotion features={domMax} strict>
        <MotionConfig reducedMotion="user" transition={{ type: 'spring', stiffness: 260, damping: 26 }}>
          <Notifications position="top-right" />
          <App />
        </MotionConfig>
      </LazyMotion>
    </MantineProvider>
  </StrictMode>,
)
