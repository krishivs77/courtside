import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';

const source = readFileSync(new URL('../src/lib/player-analytics.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { performanceSeries } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const games = [10, 20, 30, 40, 50, 60].map((points, index) => ({
  game_date: `2025-10-${21 + index}`, points, assists: index, is_home: index % 2 === 0, opponent_abbreviation: 'LAL',
}));

test('trailing averages never include future games and drop old appearances', () => {
  const result = performanceSeries(games, 'points');
  assert.deepEqual(result.map(item => item.average), [10, 15, 20, 25, 30, 40]);
  assert.deepEqual(result.map(item => item.sample), [1, 2, 3, 4, 5, 5]);
  assert.equal(result[0].opponent, 'vs. LAL');
  assert.equal(result[1].opponent, '@ LAL');
});

test('selected metric, short windows and empty histories', () => {
  assert.deepEqual(performanceSeries([], 'points'), []);
  assert.deepEqual(performanceSeries(games.slice(0, 2), 'assists').map(item => item.average), [0, 0.5]);
});
