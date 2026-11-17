"use client";

import { FormEvent, useState } from "react";

type Player = {
  id: number;
  external_id: string;
  full_name: string;
  position: string | null;
  current_team_id: number | null;
};

export default function PlayerSearch() {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const search = query.trim();
    if (search.length < 2) return;

    setLoading(true);
    setError("");
    setPlayers([]);
    setSearched(false);

    try {
      const response = await fetch(
        `/api/players?search=${encodeURIComponent(search)}`
      );

      if (!response.ok) {
        throw new Error("Unable to search players");
      }

      const data: Player[] = await response.json();
      setPlayers(data);
      setSearched(true);
    } catch {
      setError("Could not load players. Check the backend connection.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={handleSearch} className="mb-10 flex max-w-2xl gap-3">
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search Curry, LeBron, Wembanyama..."
          aria-label="Search NBA players"
          maxLength={100}
          className="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/5 px-5 py-4 text-white outline-none placeholder:text-slate-500 focus:border-orange-500"
        />

        <button
          type="submit"
          disabled={loading || query.trim().length < 2}
          className="rounded-xl bg-orange-500 px-6 font-bold text-black transition hover:bg-orange-400 disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && (
        <p role="alert" className="mb-6 text-red-400">
          {error}
        </p>
      )}

      {searched && (
        <p className="mb-5 text-sm text-slate-400" role="status">
          {players.length} matching players found
        </p>
      )}

      {searched && players.length === 0 && (
        <div className="rounded-2xl border border-white/10 p-10 text-center text-slate-400">
          No players found. Try another name.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {players.map((player) => (
          <article
            key={player.id}
            className="rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:border-orange-500/40"
          >
            <div className="mb-7 flex h-14 w-14 items-center justify-center rounded-xl bg-orange-500/10 text-xl font-black text-orange-400">
              {player.full_name
                .split(" ")
                .map((part) => part[0])
                .slice(0, 2)
                .join("")}
            </div>

            <h2 className="text-xl font-bold">
              {player.full_name}
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              {player.position ?? "Position not yet available"}
            </p>

            <div className="mt-6 border-t border-white/10 pt-4">
              <p className="text-xs text-slate-500">
                NBA ID: {player.external_id}
              </p>
              <p className="mt-2 text-xs text-orange-400">
                Performance analytics coming soon
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
