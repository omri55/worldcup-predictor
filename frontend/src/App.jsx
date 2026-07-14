import { useEffect, useState } from "react";
import { api } from "./api.js";
import MatchCard from "./components/MatchCard.jsx";
import PredictTool from "./components/PredictTool.jsx";
import Simulation from "./components/Simulation.jsx";
import Picks from "./components/Picks.jsx";
import About from "./components/About.jsx";
import { flag } from "./flags.js";

function AwaitingNote({ awaiting }) {
  if (!awaiting.length) return null;
  return (
    <details className="awaiting">
      <summary>
        ⏳ {awaiting.length} משחקים כבר שוחקו וממתינים לתוצאה מהמקור (לא ניתן לנחש)
      </summary>
      <div className="awaiting-list">
        {awaiting.map((m, i) => (
          <span key={i} className="awaiting-item" dir="ltr">
            {m.date} · {m.home_team} – {m.away_team}
          </span>
        ))}
      </div>
    </details>
  );
}

function StrategyToggle({ aggressive, onChange }) {
  return (
    <div className="strategy">
      <span className="strategy-label">אסטרטגיה:</span>
      <div className="strategy-btns">
        <button
          className={!aggressive ? "active" : ""}
          onClick={() => onChange(false)}
        >
          🎯 אופטימלי
        </button>
        <button
          className={aggressive ? "active" : ""}
          onClick={() => onChange(true)}
        >
          🔥 מצב רדיפה
        </button>
      </div>
      <span className="strategy-hint">
        {aggressive
          ? "נועז במשחקים הצפופים — לסגירת פער כשאתה מאחור"
          : "תוחלת הנקודות הגבוהה ביותר — מומלץ כברירת מחדל / כשאתה מוביל"}
      </span>
    </div>
  );
}

function Ranking({ ranking }) {
  return (
    <div className="ranking">
      <h2>דירוג Elo עולמי 🌍</h2>
      <ol className="ranking-list">
        {ranking.map((r) => (
          <li key={r.team}>
            <span className="rank-num">{r.rank}</span>
            <span className="rank-team"><span className="flag">{flag(r.team)}</span> {r.team}</span>
            <span className="rank-elo">{r.elo}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

const TABS = [
  { id: "upcoming", label: "משחקים קרובים" },
  { id: "picks", label: "הניחושים שלי 📋" },
  { id: "simulation", label: "סיכויי זכייה 🏆" },
  { id: "predict", label: "חזה משחק" },
  { id: "played", label: "דיוק המודל" },
  { id: "ranking", label: "דירוג נבחרות" },
  { id: "about", label: "איך זה עובד 🧠" },
];

export default function App() {
  const [tab, setTab] = useState("upcoming");
  const [status, setStatus] = useState(null);
  const [teams, setTeams] = useState([]);
  const [upcoming, setUpcoming] = useState([]);
  const [awaiting, setAwaiting] = useState([]);
  const [played, setPlayed] = useState(null);
  const [ranking, setRanking] = useState([]);
  const [aggressive, setAggressive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [st, tm, up, pl, rk] = await Promise.all([
          api.status(),
          api.teams(),
          api.upcoming(),
          api.played(),
          api.ranking(30),
        ]);
        setStatus(st);
        setTeams(tm.teams);
        setUpcoming(up.matches);
        setAwaiting(up.awaiting_result || []);
        setPlayed(pl);
        setRanking(rk.ranking);
      } catch (e) {
        setError("לא הצלחנו לטעון את הנתונים — בדוק את חיבור האינטרנט ונסה לרענן.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1><span className="logo-emoji">⚽</span> חיזוי מונדיאל 2026</h1>
        <p className="tagline">
          Dixon-Coles + Elo + שוק ההימורים · {status?.matches_in_training?.toLocaleString() ?? "…"} משחקים באימון
        </p>
        {status?.trained_at && (
          <p className="updated">
            עודכן לאחרונה: {new Date(status.trained_at).toLocaleString("he-IL")}
          </p>
        )}
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "tab active" : "tab"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="content">
        {loading && <div className="loading">טוען חיזויים…</div>}
        {error && (
          <div className="error">
            <p>{error}</p>
            <button onClick={() => window.location.reload()}>רענן</button>
          </div>
        )}

        {!loading && !error && (
          <>
            {tab === "upcoming" && (
              <>
                <AwaitingNote awaiting={awaiting} />
                <StrategyToggle aggressive={aggressive} onChange={setAggressive} />
                <div className="grid">
                  {upcoming.length === 0 && <p>אין כרגע משחקים עתידיים בלוח.</p>}
                  {upcoming.map((m, i) => (
                    <MatchCard key={`${m.date}-${m.home_team}-${i}`} match={m} aggressive={aggressive} />
                  ))}
                </div>
              </>
            )}

            {tab === "picks" && (
              <>
                <AwaitingNote awaiting={awaiting} />
                <StrategyToggle aggressive={aggressive} onChange={setAggressive} />
                <Picks matches={upcoming} aggressive={aggressive} />
              </>
            )}

            {tab === "simulation" && <Simulation />}

            {tab === "predict" && <PredictTool teams={teams} />}

            {tab === "played" && played && (
              <div>
                {played.model_accuracy_so_far != null && (
                  <>
                    <div className="points-banner">
                      <span className="points-label">🏆 המודל צבר בליגה</span>
                      <span className="points-value">{played.points}</span>
                      <span className="points-sub">
                        נקודות מתוך {played.points_max} אפשריות ({played.total} משחקים)
                      </span>
                    </div>
                    <div className="accuracy-banner">
                      <div className="acc-metric">
                        <span className="acc-label">דיוק כיוון (מי ניצח/תיקו)</span>
                        <b>{(played.model_accuracy_so_far * 100).toFixed(0)}%</b>
                        <span className="acc-sub">{played.hits}/{played.total}</span>
                      </div>
                      <div className="acc-metric">
                        <span className="acc-label">דיוק תוצאה מדויקת</span>
                        <b>{(played.exact_accuracy * 100).toFixed(0)}%</b>
                        <span className="acc-sub">{played.exact_hits}/{played.total}</span>
                      </div>
                    </div>
                  </>
                )}
                <div className="grid">
                  {played.matches.length === 0 && <p>עדיין לא שוחקו משחקי מונדיאל.</p>}
                  {[...played.matches]
                    .sort((a, b) => b.date.localeCompare(a.date)) // החדשים למעלה
                    .map((m, i) => (
                      <MatchCard key={`${m.date}-${m.home_team}-${i}`} match={m} />
                    ))}
                </div>
              </div>
            )}

            {tab === "ranking" && <Ranking ranking={ranking} />}

            {tab === "about" && <About status={status} />}
          </>
        )}
      </main>

      <footer className="app-footer">
        מקור נתונים: martj42/international_results (CC0) · המודל אינו ייעוץ הימורים
      </footer>
    </div>
  );
}
