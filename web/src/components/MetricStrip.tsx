export type Metric = { label: string; value: string; tone?: 'negative' | 'positive' | 'neutral' }

export function MetricStrip({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="metric-strip">
      {metrics.map((metric) => (
        <div className="metric" key={metric.label}>
          <span>{metric.label}</span>
          <strong className={metric.tone ? `tone-${metric.tone}` : ''}>{metric.value}</strong>
        </div>
      ))}
    </div>
  )
}

