import { useEffect, useState } from "react";
import { api } from "../api.js";

const pct = (x) => `${(x * 100).toFixed(x >= 0.1 ? 0 : 1)}%`;

function WinBar({ value, max }) {
  const w = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="winbar-track">
      <div className="winbar-fill" style={{ width: `${w}%` }} />
      <span className="winbar-label">{pct(value)}</span>
    </div>
  );
}

export default function Simulation() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [groupFilter, setGroupFilter] = useState("ALL");

  useEffect(() => {
    api
      .simulation(4000)
      .then(setData)
      .catch(() => setError("הסימולציה עדיין נטענת. נסה שוב בעוד רגע."));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="loading">מריץ 4,000 סימולציות של הטורניר…</div>;

  const groups = Object.keys(data.groups).sort();
  let teams = data.teams;
  if (groupFilter !== "ALL") {
    teams = teams.filter((t) => t.group === groupFilter);
  }
  const maxWin = Math.max(...data.teams.map((t) => t.win_cup), 0.0001);

  return (
    <section className="simulation">
      <div className="sim-head">
        <div>
          <h2>סימולציית מונטה-קרלו 🎲</h2>
          <p className="muted">
            {data.simulations.toLocaleString()} ריצות מלאות של הטורניר — שלב הבתים
            (כולל תוצאות אמת שכבר נקבעו) ועד הגמר.
          </p>
        </div>
        <select value={groupFilter} onChange={(e) => setGroupFilter(e.target.value)}>
          <option value="ALL">כל הבתים</option>
          {groups.map((g) => (
            <option key={g} value={g}>בית {g}</option>
          ))}
        </select>
      </div>

      <div className="sim-table-wrap">
        <table className="sim-table">
          <thead>
            <tr>
              <th>#</th>
              <th>נבחרת</th>
              <th>בית</th>
              <th>העפלה</th>
              <th>רבע גמר</th>
              <th>חצי גמר</th>
              <th>גמר</th>
              <th>זכייה 🏆</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((t, i) => (
              <tr key={t.team}>
                <td className="dim">{i + 1}</td>
                <td className="team-cell">{t.team}</td>
                <td className="dim">{t.group}</td>
                <td>{pct(t.advance)}</td>
                <td>{pct(t.reach_qf)}</td>
                <td>{pct(t.reach_sf)}</td>
                <td>{pct(t.reach_final)}</td>
                <td className="win-cell"><WinBar value={t.win_cup} max={maxWin} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
