/**
 * AttentionChart — real-time line chart of attention score over time.
 * Uses react-chartjs-2 with Chart.js.
 */
import {
  Chart as ChartJS, CategoryScale, LinearScale,
  PointElement, LineElement, Filler, Tooltip,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

const MAX_POINTS = 60

export default function AttentionChart({ history = [] }) {
  const trimmed = history.slice(-MAX_POINTS)
  const labels  = trimmed.map((_, i) => i === trimmed.length - 1 ? 'Now' : '')

  const data = {
    labels,
    datasets: [
      {
        label: 'Attention',
        data: trimmed,
        borderColor: 'rgba(0,212,255,0.9)',
        backgroundColor: 'rgba(0,212,255,0.07)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    scales: {
      x: { display: false },
      y: {
        min: 0, max: 1,
        grid:  { color: 'rgba(255,255,255,0.04)' },
        ticks: {
          color: '#4a5a7a',
          font: { size: 10, family: 'JetBrains Mono' },
          callback: v => `${Math.round(v * 100)}%`,
          stepSize: 0.25,
        },
        border: { display: false },
      },
    },
    plugins: { legend: { display: false }, tooltip: {
      backgroundColor: 'rgba(12,18,32,0.95)',
      borderColor: 'rgba(0,212,255,0.3)',
      borderWidth: 1,
      titleColor: '#8899bb',
      bodyColor: '#f0f6ff',
      callbacks: { label: ctx => ` ${Math.round(ctx.raw * 100)}%` },
    }},
  }

  return (
    <div>
      <div className="section-header">
        <span className="section-title">Attention Over Time</span>
        <span style={{ fontSize: '0.75rem', color: 'var(--cyan)', fontFamily: 'var(--font-mono)' }}>
          {trimmed.length > 0 ? `${Math.round(trimmed[trimmed.length-1] * 100)}%` : '--'}
        </span>
      </div>
      <div className="chart-wrapper">
        <Line data={data} options={options} />
      </div>
    </div>
  )
}
