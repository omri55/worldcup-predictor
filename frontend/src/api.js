// Data layer with two modes:
//   * dev  -> talk to the live FastAPI backend (/api), full features.
//   * build (static / GitHub Pages) -> read the prebuilt data.json once.
// The app is identical either way; only the data source changes.
const DEV = import.meta.env.DEV;
export const IS_STATIC = !DEV;

async function getDev(path) {
  const res = await fetch(`/api${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// Load data.json once, shared across all callers, with automatic retries so a
// transient network hiccup (or a mid-deploy moment) doesn't break the app.
let _promise = null;
function loadStatic() {
  if (!_promise) _promise = fetchWithRetry();
  return _promise;
}

async function fetchWithRetry(attempts = 4) {
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(`${import.meta.env.BASE_URL}data.json`);
      if (!res.ok) throw new Error(`data.json ${res.status}`);
      return await res.json();
    } catch (e) {
      lastErr = e;
      await new Promise((r) => setTimeout(r, 700 * (i + 1)));
    }
  }
  _promise = null; // allow a later call to try again
  throw lastErr;
}

export const api = {
  status: async () => (DEV ? getDev("/status") : (await loadStatic()).status),
  teams: async () =>
    DEV ? getDev("/teams") : { teams: (await loadStatic()).wc_teams },
  ranking: async (top = 30) =>
    DEV
      ? getDev(`/ranking?top=${top}`)
      : { ranking: (await loadStatic()).ranking.slice(0, top) },
  upcoming: async (year = 2026) =>
    DEV ? getDev(`/worldcup/upcoming?year=${year}`) : (await loadStatic()).upcoming,
  played: async (year = 2026) =>
    DEV ? getDev(`/worldcup/played?year=${year}`) : (await loadStatic()).played,
  simulation: async (n = 4000) =>
    DEV ? getDev(`/worldcup/simulation?n=${n}`) : (await loadStatic()).simulation,
  predict: async (home, away, neutral = true, stage = "group") => {
    if (DEV) {
      return getDev(
        `/predict?home=${encodeURIComponent(home)}&away=${encodeURIComponent(
          away
        )}&neutral=${neutral}&stage=${stage}`
      );
    }
    const d = await loadStatic();
    const pred = d.predict[`${home}|${away}`];
    if (!pred) throw new Error("no prediction for this matchup");
    return { home_team: home, away_team: away, neutral, stage: "group", prediction: pred };
  },
};
