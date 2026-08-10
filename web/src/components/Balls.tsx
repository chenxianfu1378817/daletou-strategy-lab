type Props = { front: number[]; back: number[]; size?: 'sm' | 'md' }

export function Balls({ front, back, size = 'md' }: Props) {
  return (
    <div className={`balls balls--${size}`} aria-label={`前区 ${front.join(' ')}，后区 ${back.join(' ')}`}>
      <div className="balls__group">
        {front.map((number) => <span className="ball ball--front" key={`f-${number}`}>{String(number).padStart(2, '0')}</span>)}
      </div>
      <span className="balls__divider" aria-hidden="true" />
      <div className="balls__group">
        {back.map((number) => <span className="ball ball--back" key={`b-${number}`}>{String(number).padStart(2, '0')}</span>)}
      </div>
    </div>
  )
}

