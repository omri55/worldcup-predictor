import ProbBar from "./ProbBar.jsx";
import { chosenPick } from "../pickMode.js";

const flag = (team) => team; // placeholder for future flag emojis

function outcomeLabel(outcome, home, away) {
  if (outcome === "home") return `ניצחון ${home}`;
  if (outcome === "away") return `ניצחון ${away}`;
  return "תיקו";
}

const STAGE_NAMES = {
  r32: "שלב ה-32",
  r16: "שמינית גמר",
  qf: "רבע גמר",
  sf: "חצי גמר",
  third: "מקום שלישי",
  final: "גמר 🏆",
};

function ConfidenceBadge({ value }) {
  const level = value > 0.6 ? "high" : value > 0.3 ? "mid" : "low";
  const label = { high: "ביטחון גבוה", mid: "ביטחון בינוני", low: "ביטחון נמוך" }[level];
  return <span className={`badge badge-${level}`}>{label}</span>;
}

export default function MatchCard({ match, aggressive = false }) {
  const p = match.prediction;
  const actual = match.actual;
  const pick = chosenPick(p, aggressive);
  return (
    <div className="card match-card">
      <div className="match-head">
        <span className="match-date">{match.date}</span>
        {match.stage && match.stage !== "group" && (
          <span className="stage-badge">{STAGE_NAMES[match.stage] || match.stage}</span>
        )}
        {match.city && <span className="match-venue">{match.city}, {match.country}</span>}
        <ConfidenceBadge value={p.confidence} />
      </div>

      <div className="match-teams">
        <div className="team team-home">
          <span className="team-name">{flag(match.home_team)}</span>
          <span className="team-elo">Elo {p.elo_home}</span>
        </div>
        <div className="match-score">
          {actual ? (
            <span className="score-final">{actual.score}</span>
          ) : (
            <span className="score-pred">{pick.score}</span>
          )}
          <span className="score-sub">
            {actual ? "תוצאה" : pick.isGamble ? "ניחוש נועז 🔥" : "הניחוש המומלץ"}
          </span>
        </div>
        <div className="team team-away">
          <span className="team-name">{flag(match.away_team)}</span>
          <span className="team-elo">Elo {p.elo_away}</span>
        </div>
      </div>

      <ProbBar
        home={p.prob_home}
        draw={p.prob_draw}
        away={p.prob_away}
        homeLabel={match.home_team}
        awayLabel={match.away_team}
      />

      <div className={`pick ${pick.isGamble ? "pick-gamble" : ""}`}>
        <span className="pick-out">
          {pick.isGamble ? "🔥" : "🎯"} {outcomeLabel(pick.outcome, match.home_team, match.away_team)}
        </span>
        <span className="pick-ev-tag">תוחלת <b>{pick.ev.toFixed(2)}</b> נק'</span>
      </div>

      <div className="signal">
        {p.market_used ? (
          <span className="signal-on">📊 כולל שוק ההימורים · {p.market_bookmakers} בוקמייקרים</span>
        ) : (
          <span className="signal-off">מבוסס מודל סטטיסטי (Dixon-Coles + Elo)</span>
        )}
      </div>

      <div className="markets">
        <div className="market">
          <span>גולים צפויים (xG)</span><b dir="ltr">{p.xg_home} – {p.xg_away}</b>
        </div>
        <div className="market">
          <span>מעל 2.5</span><b>{(p.over_2_5 * 100).toFixed(0)}%</b>
        </div>
        <div className="market">
          <span>שתי הקבוצות יבקיעו</span><b>{(p.btts_yes * 100).toFixed(0)}%</b>
        </div>
        <div className="market">
          <span>התוצאה הסבירה ביותר (רקע)</span><b>{p.likely_score} ({(p.likely_score_prob * 100).toFixed(0)}%)</b>
        </div>
      </div>

      {p.margins && (
        <div className="margins">
          <div className="margins-title">מרווח ניצחון צפוי</div>
          <div className="margins-list">
            {[
              { k: "home2", label: `${match.home_team} +2` },
              { k: "home1", label: `${match.home_team} +1` },
              { k: "draw", label: "תיקו" },
              { k: "away1", label: `${match.away_team} +1` },
              { k: "away2", label: `${match.away_team} +2` },
            ]
              .filter((x) => p.margins[x.k] >= 0.03)
              .map((x) => (
                <span key={x.k} className="margin-chip">
                  {x.label} <b>{(p.margins[x.k] * 100).toFixed(0)}%</b>
                </span>
              ))}
          </div>
        </div>
      )}

      <details className="topscores">
        <summary>תוצאות סבירות נוספות</summary>
        <div className="topscores-list">
          {p.top_scores.map((s) => (
            <span key={s.score} className="topscore">
              {s.score} · {(s.prob * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      </details>

      {actual && (
        <div className={`hit ${match.prediction_hit ? "hit-yes" : "hit-no"}`}>
          {match.exact_hit
            ? "🎯 תוצאה מדויקת!"
            : match.prediction_hit
            ? "✓ כיוון נכון"
            : "✗ פספוס"}
        </div>
      )}
    </div>
  );
}
