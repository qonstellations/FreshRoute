import { type CSSProperties } from 'react'

export function LowPolyTomato({ style, className }: { style?: CSSProperties; className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
      className={`low-poly-svg ${className ?? ''}`}
      style={style}
    >
      {/* Faceted Body */}
      <polygon points="50,20 75,28 90,52 80,78 50,90 20,78 10,52 25,28" fill="currentColor" fillOpacity="0.08" />
      <polygon points="50,20 62,38 75,28" />
      <polygon points="75,28 62,38 78,55 90,52" />
      <polygon points="90,52 78,55 70,72 80,78" />
      <polygon points="80,78 70,72 50,78 50,90" />
      <polygon points="50,90 50,78 30,72 20,78" />
      <polygon points="20,78 30,72 22,55 10,52" />
      <polygon points="10,52 22,55 38,38 25,28" />
      <polygon points="25,28 38,38 50,20" />
      <polygon points="50,20 62,38 50,55 38,38" />
      <polygon points="38,38 50,55 30,72 22,55" />
      <polygon points="62,38 78,55 70,72 50,55" />
      <polygon points="50,55 70,72 50,78 30,72" />
      {/* Stem / Calyx */}
      <polygon points="50,10 52,20 48,20" fill="currentColor" opacity="0.6" />
      <polygon points="50,20 42,14 46,22" />
      <polygon points="50,20 58,14 54,22" />
      <polygon points="50,20 50,26" />
    </svg>
  )
}

export function LowPolyMango({ style, className }: { style?: CSSProperties; className?: string }) {
  return (
    <svg
      viewBox="0 0 100 120"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
      className={`low-poly-svg ${className ?? ''}`}
      style={style}
    >
      <polygon points="50,15 72,25 85,55 80,85 62,108 40,112 25,95 20,60 32,30" fill="currentColor" fillOpacity="0.08" />
      <polygon points="50,15 62,35 72,25" />
      <polygon points="72,25 62,35 75,58 85,55" />
      <polygon points="85,55 75,58 72,82 80,85" />
      <polygon points="80,85 72,82 58,98 62,108" />
      <polygon points="62,108 58,98 42,102 40,112" />
      <polygon points="40,112 42,102 30,90 25,95" />
      <polygon points="25,95 30,90 28,65 20,60" />
      <polygon points="20,60 28,65 38,40 32,30" />
      <polygon points="32,30 38,40 50,15" />
      <polygon points="50,15 38,40 50,58 62,35" />
      <polygon points="62,35 50,58 72,82 75,58" />
      <polygon points="38,40 28,65 42,75 50,58" />
      <polygon points="50,58 42,75 58,98 72,82" />
      <polygon points="42,75 28,65 30,90 42,102 58,98" />
      {/* Stem */}
      <line x1="50" y1="15" x2="48" y2="6" strokeWidth="2" />
    </svg>
  )
}

export function LowPolyBanana({ style, className }: { style?: CSSProperties; className?: string }) {
  return (
    <svg
      viewBox="0 0 110 90"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
      className={`low-poly-svg ${className ?? ''}`}
      style={style}
    >
      <polygon points="15,20 30,12 55,18 80,32 95,55 90,75 80,78 68,62 48,42 30,30 18,25" fill="currentColor" fillOpacity="0.08" />
      <polygon points="15,20 30,12 30,22 18,25" />
      <polygon points="30,12 55,18 48,30 30,22" />
      <polygon points="55,18 80,32 68,45 48,30" />
      <polygon points="80,32 95,55 82,62 68,45" />
      <polygon points="95,55 90,75 80,78 82,62" />
      <polygon points="18,25 30,22 48,30 30,30" />
      <polygon points="30,30 48,30 68,45 48,42" />
      <polygon points="48,42 68,45 82,62 68,62" />
      <polygon points="68,62 82,62 80,78" />
      {/* Stem tip */}
      <line x1="15" y1="20" x2="8" y2="24" strokeWidth="2.5" />
    </svg>
  )
}

export function LowPolySpinach({ style, className }: { style?: CSSProperties; className?: string }) {
  return (
    <svg
      viewBox="0 0 90 110"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
      className={`low-poly-svg ${className ?? ''}`}
      style={style}
    >
      <polygon points="45,10 65,25 78,50 72,80 52,98 45,105 38,98 18,80 12,50 25,25" fill="currentColor" fillOpacity="0.08" />
      <polygon points="45,10 52,32 65,25" />
      <polygon points="65,25 52,32 62,55 78,50" />
      <polygon points="78,50 62,55 58,78 72,80" />
      <polygon points="72,80 58,78 48,92 52,98" />
      <polygon points="52,98 48,92 45,105" />
      <polygon points="45,105 42,92 38,98" />
      <polygon points="38,98 42,92 32,78 18,80" />
      <polygon points="18,80 32,78 28,55 12,50" />
      <polygon points="12,50 28,55 38,32 25,25" />
      <polygon points="25,25 38,32 45,10" />
      <polygon points="45,10 38,32 45,52 52,32" />
      <polygon points="38,32 28,55 38,68 45,52" />
      <polygon points="52,32 45,52 52,68 62,55" />
      <polygon points="45,52 38,68 45,82 52,68" />
      <polygon points="38,68 32,78 42,92 45,82" />
      <polygon points="52,68 45,82 48,92 58,78" />
      {/* Midrib */}
      <line x1="45" y1="10" x2="45" y2="105" strokeWidth="1.8" />
    </svg>
  )
}

export function LowPolyCarrot({ style, className }: { style?: CSSProperties; className?: string }) {
  return (
    <svg
      viewBox="0 0 90 120"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
      className={`low-poly-svg ${className ?? ''}`}
      style={style}
    >
      <polygon points="45,25 65,30 60,60 52,90 46,115 44,115 38,90 30,60 25,30" fill="currentColor" fillOpacity="0.08" />
      <polygon points="45,25 55,42 65,30" />
      <polygon points="65,30 55,42 54,68 60,60" />
      <polygon points="60,60 54,68 48,95 52,90" />
      <polygon points="52,90 48,95 46,115" />
      <polygon points="46,115 44,115 42,95" />
      <polygon points="44,115 42,95 38,90" />
      <polygon points="38,90 42,95 36,68 30,60" />
      <polygon points="30,60 36,68 35,42 25,30" />
      <polygon points="25,30 35,42 45,25" />
      <polygon points="45,25 35,42 45,58 55,42" />
      <polygon points="35,42 36,68 45,78 45,58" />
      <polygon points="55,42 45,58 45,78 54,68" />
      <polygon points="45,78 36,68 42,95 45,95" />
      <polygon points="45,78 45,95 48,95 54,68" />
      {/* Foliage leaves */}
      <polyline points="45,25 45,8 40,2" />
      <polyline points="45,25 52,10 60,6" />
      <polyline points="45,25 38,12 30,8" />
    </svg>
  )
}
