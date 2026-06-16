import { useState } from "react";
import { api, IS_STATIC } from "../api.js";
import MatchCard from "./MatchCard.jsx";

export default function PredictTool({ teams }) {
  const [home, setHome] = useState("Brazil");
  const [away, setAway] = useState("Argentina");
  const [neutral, setNeutral] = useState(true);
  const [stage, setStage] = useState("group");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.predict(home, away, neutral, stage);
      setResult({
        date: "חיזוי מותאם",
        home_team: r.home_team,
        away_team: r.away_team,
        prediction: r.prediction,
      });
    } catch (e) {
      setError("לא ניתן לחזות — בדוק שמות קבוצות.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="predict-tool">
      <h2>חזה כל משחק 🔮</h2>
      <p className="muted">בחר שתי נבחרות וקבל חיזוי מלא — שימושי למשחקי ניחושים עם חברים.</p>
      <div className="predict-controls">
        <select value={home} onChange={(e) => setHome(e.target.value)}>
          {teams.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <span className="vs">נגד</span>
        <select value={away} onChange={(e) => setAway(e.target.value)}>
          {teams.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        {!IS_STATIC && (
          <select value={stage} onChange={(e) => setStage(e.target.value)} title="שלב בטורניר (משפיע על ניקוד הניחוש)">
            <option value="group">שלב בתים (3/1)</option>
            <option value="r32">1/16 גמר (5/2)</option>
            <option value="r16">שמינית גמר (5/2)</option>
            <option value="qf">רבע גמר (8/4)</option>
            <option value="sf">חצי גמר (10/5)</option>
            <option value="third">מקום 3 (10/5)</option>
            <option value="final">גמר (15/8)</option>
          </select>
        )}
        <label className="neutral-toggle">
          <input
            type="checkbox"
            checked={neutral}
            onChange={(e) => setNeutral(e.target.checked)}
          />
          מגרש ניטרלי
        </label>
        <button onClick={run} disabled={loading || home === away}>
          {loading ? "מחשב…" : "חזה"}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {result && <MatchCard match={result} />}
    </section>
  );
}
