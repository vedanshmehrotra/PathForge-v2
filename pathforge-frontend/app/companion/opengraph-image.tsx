import { ImageResponse } from 'next/og'

export const alt = 'PathForge Companion — understand your LeetCode Python patterns'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'
export default function Image() {
  return new ImageResponse(
    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', width: '100%', height: '100%', background: '#101213', color: '#ededed', padding: 80 }}>
      <div style={{ display: 'flex', fontSize: 26, color: '#7cbaaa', marginBottom: 45 }}>PATHFORGE COMPANION</div>
      <div style={{ display: 'flex', fontSize: 76, fontWeight: 700, letterSpacing: -3 }}>Find the pattern</div>
      <div style={{ display: 'flex', fontSize: 76, fontWeight: 700, letterSpacing: -3 }}>in your own code.</div>
      <div style={{ display: 'flex', fontSize: 26, color: '#aaaeb6', marginTop: 42 }}>LeetCode · Python · Firefox</div>
    </div>, size,
  )
}
