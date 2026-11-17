export type PlayerProfile = {
  id: number;
  external_id: string;
  full_name: string;
  position: string | null;
  current_team_id: number | null;
};

export type PlayerGame = {
  game_id: number;
  external_id: string;
  game_date: string;
  season: string;
  season_type: string;
  opponent_abbreviation: string;
  opponent_name: string;
  team_abbreviation: string;
  is_home: boolean;
  minutes: number | null;
  points: number;
  rebounds: number;
  assists: number;
  fgm: number;
  fga: number;
  three_pm: number;
  three_pa: number;
  source: string | null;
  retrieved_at: string | null;
};

export type PlayerGamesResponse = {
  player: PlayerProfile;
  games: PlayerGame[];
  total: number;
  limit: number;
  offset: number;
};

export type Metric = "points" | "rebounds" | "assists" | "three_pm";

// Each mean uses only this game and earlier appearances in the loaded window.
export function performanceSeries(games: PlayerGame[], metric: Metric, rollingWindow = 5) {
  return games.map((game, index) => {
    const trailing = games.slice(Math.max(0, index - rollingWindow + 1), index + 1);
    return {
      date: game.game_date,
      opponent: `${game.is_home ? "vs." : "@"} ${game.opponent_abbreviation}`,
      value: game[metric],
      average: trailing.reduce((sum, item) => sum + item[metric], 0) / trailing.length,
      sample: trailing.length,
    };
  });
}
