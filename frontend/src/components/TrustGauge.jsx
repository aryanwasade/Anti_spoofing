/**
 * TrustGauge — circular SVG gauge showing a 0-100% value.
 * Color: green >70%, amber 40-70%, red <40%
 */
export default function TrustGauge({ value = 0, label = 'Trust Score', size = 140 }) {
  const pct      = Math.max(0, Math.min(100, Math.round(value * 100)))
  const radius   = (size / 2) - 14
  const circ     = 2 * Math.PI * radius
  const dash     = circ * (pct / 100)
  const gap      = circ - dash

  const color = pct >= 70 ? '#34d399'    // emerald
              : pct >= 40 ? '#fbbf24'    // amber
              :             '#fb7185'    // rose

  const trackColor = 'rgba(255,255,255,0.05)'

  return (
    <div className="gauge-container">
      <svg
        width={size}
        height={size}
        className="gauge-svg"
        viewBox={`0 0 ${size} ${size}`}
        aria-label={`${label}: ${pct}%`}
      >
        {/* Track */}
        <circle
          className="gauge-track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={10}
          stroke={trackColor}
        />
        {/* Fill */}
        <circle
          className={`gauge-fill ${pct < 40 ? 'animating' : ''}`}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={10}
          stroke={color}
          strokeDasharray={`${dash} ${gap}`}
          strokeDashoffset={0}
          style={{ filter: `drop-shadow(0 0 6px ${color}60)` }}
        />
        {/* Center text */}
        <g className="gauge-text-group">
          <text
            x={size / 2}
            y={size / 2 - 4}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={color}
            fontSize={size * 0.18}
            fontWeight="800"
            fontFamily="JetBrains Mono, monospace"
          >
            {pct}%
          </text>
          <text
            x={size / 2}
            y={size / 2 + size * 0.14}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="rgba(148,163,184,0.8)"
            fontSize={size * 0.09}
            fontWeight="600"
            fontFamily="Inter, sans-serif"
          >
            {label}
          </text>
        </g>
      </svg>
    </div>
  )
}
