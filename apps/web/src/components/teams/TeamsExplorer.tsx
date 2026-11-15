"use client";

import { useMemo, useState } from "react";

export type Team = {
  id: number;
  external_id: string;
  name: string;
  abbreviation: string;
  conference: string | null;
};

type ConferenceFilter = "All" | "East" | "West";

const filters: ConferenceFilter[] = ["All", "East", "West"];

export default function TeamsExplorer({ teams }: { teams: Team[] }) {
  const [search, setSearch] = useState("");
  const [conference, setConference] =
    useState<ConferenceFilter>("All");

  const filteredTeams = useMemo(() => {
    const query = search.trim().toLowerCase();

    return teams.filter((team) => {
      const matchesSearch =
        team.name.toLowerCase().includes(query) ||
        team.abbreviation.toLowerCase().includes(query);

      const matchesConference =
        conference === "All" || team.conference === conference;

      return matchesSearch && matchesConference;
    });
  }, [teams, search, conference]);

  return (
    <div>
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        {[
          { label: "NBA Teams", value: teams.length },
          {
            label: "Eastern Conference",
            value: teams.filter((t) => t.conference === "East").length,
          },
          {
            label: "Western Conference",
            value: teams.filter((t) => t.conference === "West").length,
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-2xl border border-white/10 bg-white/5 p-5"
          >
            <p className="text-sm text-slate-400">{stat.label}</p>
            <p className="mt-2 text-3xl font-bold">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search teams..."
          aria-label="Search NBA teams"
          className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-orange-500 sm:max-w-sm"
        />

        <div className="flex gap-2">
          {filters.map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setConference(filter)}
              aria-pressed={conference === filter}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                conference === filter
                  ? "bg-orange-500 text-black"
                  : "border border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              {filter === "All" ? "All Teams" : filter}
            </button>
          ))}
        </div>
      </div>

      <p className="mb-5 text-sm text-slate-500" role="status">
        Showing {filteredTeams.length} of {teams.length} teams
      </p>

      {filteredTeams.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/15 p-12 text-center">
          <p className="font-semibold">No teams found</p>
          <p className="mt-2 text-sm text-slate-400">
            Try another search or conference filter.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredTeams.map((team) => (
            <article
              key={team.id}
              className="group rounded-2xl border border-white/10 bg-white/5 p-6 transition hover:border-orange-500/50 hover:bg-white/[0.07]"
            >
              <div className="mb-8 flex items-start justify-between">
                <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-orange-500/20 bg-orange-500/10 text-sm font-black text-orange-400">
                  {team.abbreviation}
                </div>
                <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-400">
                  {team.conference === "East"
                    ? "Eastern"
                    : team.conference === "West"
                      ? "Western"
                      : "NBA"}
                </span>
              </div>

              <h2 className="text-lg font-bold transition group-hover:text-orange-400">
                {team.name}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {team.abbreviation}
              </p>

              <div className="mt-6 border-t border-white/10 pt-4">
                <span className="text-xs text-slate-500">
                  Team analytics coming soon
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
