// SyntheticBanner + StatusBanner (ARCHITECTURE §16.1: synthetic banner always shown for synthetic data).
import type { Manifest } from '../types'

export function SyntheticBanner({ show }: { show: boolean }) {
  return show ? (
    <div className="banner warn">
      SYNTHETIC DATA: figures come from a synthetic scenario or a hand-written example, not organizer data.
    </div>
  ) : null
}

export function StatusBanner({ fixture, manifest, error }:
  { fixture: boolean; manifest: Manifest | null; error: string }) {
  return (
    <>
      {fixture && <div className="banner info">No run under outputs/. Showing the example fixture (placeholder).</div>}
      {manifest?.solver?.fallback_used && (
        <div className="banner error">Solver fallback used: this plan came from the FEFO-greedy fallback, not HiGHS.</div>
      )}
      {error && <div className="banner error">{error}</div>}
    </>
  )
}
