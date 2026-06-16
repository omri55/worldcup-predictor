// Resolve which pick to show based on the chosen strategy.
//   balanced (default / "leading") -> the EV-optimal pick
//   aggressive ("trailing")        -> high-upside contrarian pick on close games
export function chosenPick(p, aggressive) {
  if (aggressive) {
    return {
      score: p.aggressive_score,
      outcome: p.aggressive_outcome,
      ev: p.aggressive_ev,
      // only a genuine gamble when it differs from the balanced pick
      isGamble: p.aggressive_score !== p.pick_score,
    };
  }
  return {
    score: p.pick_score,
    outcome: p.pick_outcome,
    ev: p.pick_ev,
    isGamble: false,
  };
}
