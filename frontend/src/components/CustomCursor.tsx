import { gsap } from 'gsap'
import { useEffect, useRef, useState } from 'react'

export function CustomCursor() {
  const cursorRef = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState(false)
  const [label, setLabel] = useState('')

  useEffect(() => {
    const el = cursorRef.current
    if (!el) return

    // Quick setters for smooth 60fps tracking without layout recalculation
    const xTo = gsap.quickTo(el, 'x', { duration: 0.18, ease: 'power3.out' })
    const yTo = gsap.quickTo(el, 'y', { duration: 0.18, ease: 'power3.out' })

    const onMouseMove = (e: MouseEvent) => {
      xTo(e.clientX)
      yTo(e.clientY)
    }

    const onMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null
      const hoverTarget = target?.closest('[data-cursor], button, a') as HTMLElement | null
      if (hoverTarget) {
        setActive(true)
        const customLabel = hoverTarget.getAttribute('data-cursor')
        setLabel(customLabel && customLabel !== 'pointer' ? customLabel : '')
      } else {
        setActive(false)
        setLabel('')
      }
    }

    window.addEventListener('mousemove', onMouseMove, { passive: true })
    document.addEventListener('mouseover', onMouseOver, { passive: true })

    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseover', onMouseOver)
    }
  }, [])

  return (
    <div
      ref={cursorRef}
      className={`fr-cursor ${active ? 'active' : ''}`}
      aria-hidden="true"
    >
      <div className="fr-cursor-box">
        {label && <span className="fr-cursor-label">{label}</span>}
      </div>
      <div className="fr-cursor-dot" />
    </div>
  )
}
