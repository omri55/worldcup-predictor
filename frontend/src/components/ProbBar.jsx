// Stacked 1X2 probability bar: home / draw / away.
export default function ProbBar({ home, draw, away, homeLabel, awayLabel }) {
  const pct = (x) => `${(x * 100).toFixed(0)}%`;
  return (
    <div className="probbar-wrap">
      <div className="probbar">
        <div className="seg seg-home" style={{ width: pct(home) }} title={`${homeLabel} ${pct(home)}`}>
          {home > 0.12 && pct(home)}
        </div>
        <div className="seg seg-draw" style={{ width: pct(draw) }} title={`תיקו ${pct(draw)}`}>
          {draw > 0.12 && pct(draw)}
        </div>
        <div className="seg seg-away" style={{ width: pct(away) }} title={`${awayLabel} ${pct(away)}`}>
          {away > 0.12 && pct(away)}
        </div>
      </div>
      <div className="probbar-legend">
        <span><i className="dot dot-home" /> {homeLabel}</span>
        <span><i className="dot dot-draw" /> תיקו</span>
        <span><i className="dot dot-away" /> {awayLabel}</span>
      </div>
    </div>
  );
}
