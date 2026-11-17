"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Metric, performanceSeries, PlayerGamesResponse } from "@/lib/player-analytics";

const metrics: { key: Metric; label: string; short: string }[] = [
  { key: "points", label: "Points", short: "PTS" },
  { key: "rebounds", label: "Rebounds", short: "REB" },
  { key: "assists", label: "Assists", short: "AST" },
  { key: "three_pm", label: "Made threes", short: "3PM" },
];
const dateLabel = (date: string) => new Date(`${date}T12:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

export default function PlayerAnalytics({ id }: { id: string }) {
  const [data, setData] = useState<PlayerGamesResponse | null>(null);
  const [windowSize, setWindowSize] = useState(20);
  const [metric, setMetric] = useState<Metric>("points");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`/api/players/${encodeURIComponent(id)}/games?limit=${windowSize}`, { signal: controller.signal });
        if (!response.ok) throw new Error(response.status === 404 ? "Player not found." : "Could not load game logs. Please try again.");
        const result: PlayerGamesResponse = await response.json();
        if (!controller.signal.aborted) setData(result);
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Unable to load player.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [id, windowSize, retry]);

  if (loading) return <section aria-live="polite" aria-busy="true" className="mt-10 animate-pulse rounded-2xl border border-white/10 bg-white/5 p-10 text-slate-400">Loading player performance…</section>;
  if (error) return <section role="alert" className="mt-10 rounded-2xl border border-red-400/20 p-8"><h1 className="text-2xl font-bold">{error}</h1><button onClick={() => setRetry(retry + 1)} className="mt-5 rounded-lg bg-orange-500 px-5 py-3 font-semibold text-black">Try again</button></section>;
  if (!data) return null;

  const games = data.games;
  const selected = metrics.find((item) => item.key === metric)!;
  const series = performanceSeries(games, metric);
  const latest = games.at(-1);
  const seasons = [...new Set(games.map((game) => game.season))].join(" / ");
  return (
    <div className="pb-12">
      <section className="py-10">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-orange-500">Player analytics · NBA</p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">{data.player.full_name}</h1>
        <p className="mt-4 text-slate-400">{data.player.position ?? "Position unavailable"} · NBA ID {data.player.external_id}</p>
        <p className="mt-2 text-sm text-slate-500">{latest ? `Last represented team: ${latest.team_abbreviation} · ${seasons} · Regular season` : "No imported performance history"}</p>
      </section>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div><h2 className="text-xl font-semibold">Recent performance</h2><p className="mt-1 text-sm text-slate-400">{games.length} of {data.total} imported games{games.length > 0 && ` · ${dateLabel(games[0].game_date)} – ${dateLabel(latest!.game_date)}`}</p></div>
        <div className="flex gap-2" role="group" aria-label="Recent game window">
          {[5, 10, 20].map((size) => <button key={size} aria-pressed={windowSize === size} onClick={() => setWindowSize(size)} className={`rounded-lg px-4 py-2 text-sm font-semibold ${windowSize === size ? "bg-orange-500 text-black" : "bg-white/5 text-slate-300 hover:bg-white/10"}`}>Last {size}</button>)}
        </div>
      </div>
      {games.length === 0 ? <section className="rounded-2xl border border-white/10 bg-white/5 p-10 text-slate-400"><h2 className="text-xl font-semibold text-white">No game logs yet</h2><p className="mt-3">This player is in the directory, but their game history has not been imported.</p></section> : <>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {metrics.map((item) => <div key={item.key} className="rounded-2xl border border-white/10 bg-white/5 p-5"><p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{item.label} / game</p><p className="mt-3 text-3xl font-bold tabular-nums">{(games.reduce((sum, game) => sum + game[item.key], 0) / games.length).toFixed(1)}</p><p className="mt-2 text-xs text-slate-500">Across {games.length} appearances</p></div>)}
        </div>
        <section className="mt-6 rounded-2xl border border-white/10 bg-white/[0.025] p-4 sm:p-6" aria-label="Performance chart">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4"><h2 className="text-xl font-semibold">{selected.label} trend</h2><label className="text-sm text-slate-400">Statistic <select value={metric} onChange={(event) => setMetric(event.target.value as Metric)} className="ml-2 rounded-lg border border-white/10 bg-[#101827] p-2 text-white">{metrics.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label></div>
          <div className="h-80 min-w-0" role="img" aria-label={`${selected.label} by game and trailing five-game mean. Exact game values appear in the table below.`}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ top: 8, right: 12, left: -20, bottom: 8 }}>
                <CartesianGrid stroke="#ffffff10" vertical={false} />
                <XAxis dataKey="date" tickFormatter={dateLabel} stroke="#94a3b8" tick={{ fontSize: 11 }} minTickGap={25} />
                <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#101827", border: "1px solid #334155", borderRadius: 10 }} labelFormatter={(label, payload) => `${label} ${payload?.[0]?.payload.opponent ?? ""}`} formatter={(value) => typeof value === "number" ? value.toFixed(1) : value} />
                <Legend />
                <Line type="linear" dataKey="value" name={selected.label} stroke="#f97316" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                <Line type="linear" dataKey="average" name="Trailing mean (up to 5 games)" stroke="#38bdf8" strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-xs leading-5 text-slate-500">Rolling mean uses up to five appearances in the selected window, including that game. Early points use fewer games. These are descriptive statistics, not forecasts.</p>
        </section>
        <section className="mt-8"><h2 className="mb-4 text-xl font-semibold">Game log</h2><div className="overflow-x-auto rounded-xl border border-white/10"><table className="w-full whitespace-nowrap text-right text-sm"><caption className="sr-only">Recent games, newest first</caption><thead className="bg-white/5 text-xs uppercase text-slate-400"><tr>{["Date", "Matchup", "MIN", "PTS", "REB", "AST", "3PM", "3PA", "FGM", "FGA"].map((label) => <th scope="col" key={label} className="px-4 py-4">{label}</th>)}</tr></thead><tbody>{[...games].reverse().map((game) => <tr key={game.game_id} className="border-t border-white/5 tabular-nums hover:bg-white/5"><th scope="row" className="px-4 py-4 font-normal text-slate-300">{game.game_date}</th><td className="px-4 py-4" title={game.opponent_name}>{game.is_home ? "vs." : "@"} {game.opponent_abbreviation}</td><td className="px-4 py-4 text-slate-400">{game.minutes?.toFixed(1) ?? "—"}</td>{[game.points, game.rebounds, game.assists, game.three_pm, game.three_pa, game.fgm, game.fga].map((value, index) => <td key={index} className={`px-4 py-4 ${index === 0 ? "font-bold text-orange-400" : "text-slate-300"}`}>{value}</td>)}</tr>)}</tbody></table></div></section>
        <p className="mt-5 text-xs leading-5 text-slate-500">Source: NBA.com via nba_api PlayerGameLog. Dates are source calendar dates; verified tipoff times are unavailable. Imported history may be incomplete.{latest?.retrieved_at && ` Latest displayed game retrieved ${new Date(latest.retrieved_at).toLocaleDateString()}.`}</p>
      </>}
    </div>
  );
}
