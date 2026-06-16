import { useMemo, useState } from "react";
import { chosenPick } from "../pickMode.js";
import { flag } from "../flags.js";

function outcomeLabel(o, home, away) {
  if (o === "home") return home;
  if (o === "away") return away;
  return "תיקו";
}

function confTag(c) {
  if (c > 0.6) return { cls: "high", txt: "גבוה" };
  if (c > 0.3) return { cls: "mid", txt: "בינוני" };
  return { cls: "low", txt: "נמוך" };
}

export default function Picks({ matches, aggressive = false }) {
  const [copied, setCopied] = useState(false);
  const [showText, setShowText] = useState(false);

  // group by date for readability
  const byDate = useMemo(() => {
    const g = {};
    for (const m of matches) (g[m.date] ||= []).push(m);
    return Object.entries(g).sort(([a], [b]) => a.localeCompare(b));
  }, [matches]);

  const copyText = useMemo(
    () =>
      matches
        .map((m) => {
          const pick = chosenPick(m.prediction, aggressive);
          return `${m.date}  ${m.home_team} - ${m.away_team}  →  ${pick.score}`;
        })
        .join("\n"),
    [matches, aggressive]
  );

  async function copy() {
    let ok = false;
    try {
      await navigator.clipboard.writeText(copyText);
      ok = true;
    } catch {
      // Fallback for browsers / iframes where the async clipboard API is blocked.
      try {
        const ta = document.createElement("textarea");
        ta.value = copyText;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ok = document.execCommand("copy");
        document.body.removeChild(ta);
      } catch {
        ok = false;
      }
    }
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else {
      setShowText(true); // reveal text for manual copy
    }
  }

  if (!matches.length) return <p>אין כרגע משחקים עתידיים לניחוש.</p>;

  return (
    <section className="picks">
      <div className="picks-head">
        <div>
          <h2>הניחושים שלי 📋</h2>
          <p className="muted">
            {matches.length} משחקים · הניחוש בעל תוחלת הנקודות הגבוהה ביותר לכל משחק.
          </p>
        </div>
        <div className="picks-actions">
          <button onClick={copy} className="copy-btn">
            {copied ? "✓ הועתק" : "העתק הכל"}
          </button>
          <button onClick={() => setShowText((s) => !s)} className="text-btn">
            {showText ? "הסתר טקסט" : "הצג כטקסט"}
          </button>
        </div>
      </div>

      {showText && (
        <textarea
          className="picks-textarea"
          readOnly
          value={copyText}
          onFocus={(e) => e.target.select()}
          rows={Math.min(matches.length + 1, 18)}
        />
      )}

      {byDate.map(([date, ms]) => (
        <div key={date} className="picks-day">
          <div className="picks-date">{date}</div>
          <table className="picks-table">
            <tbody>
              {ms.map((m, i) => {
                const p = m.prediction;
                const t = confTag(p.confidence);
                const pick = chosenPick(p, aggressive);
                return (
                  <tr key={`${m.home_team}-${i}`}>
                    <td className="pk-match">
                      <span dir="ltr">{flag(m.home_team)} {m.home_team} – {m.away_team} {flag(m.away_team)}</span>
                    </td>
                    <td className={`pk-score ${pick.isGamble ? "pk-gamble" : ""}`} dir="ltr">
                      {pick.score}{pick.isGamble ? " 🔥" : ""}
                    </td>
                    <td className="pk-out">{outcomeLabel(pick.outcome, m.home_team, m.away_team)}</td>
                    <td className="pk-ev">{pick.ev.toFixed(2)} נק'</td>
                    <td className={`pk-conf pk-${t.cls}`}>{t.txt}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </section>
  );
}
