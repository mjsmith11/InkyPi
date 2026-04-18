# Scores
Plugin to show scores from my favorite sports teams

## Details
- The teams to track are Chicago White Sox, Indianapolis Colts, Indiana Pacers, Chicago Cubs, Purdue Boilermakers men's basketball, Chicago Blackhawks, Valparaiso Beacons women's volleyball, and Ball State Cardinals women's volleyball
- Make it dynamic so it only shows scores of teams that have a game in progress or a game in the last 12 hours.
- If only one team is active, it should take the whole screen.
- If multiple teams are active, split the screen space to show all active teams while maximizing the available space.
- If no teams are active, show a message that there are no active games.

## Implementation

### Data source
All score and schedule data is fetched from the public ESPN API:
- **Scoreboard** (`/apis/site/v2/sports/{sport}/{league}/scoreboard?dates=YYYYMMDD`) — fetches today's and yesterday's events to cover late-night games that bleed past midnight.
- **Schedule** (`/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule`) — used only when no active games are found, to show each team's next upcoming game.

### Tracked teams (`TRACKED_TEAMS`)
Eight hardcoded teams, each carrying `sport`, `league`, and ESPN `id`:

| Team | Sport | League | ESPN ID |
|------|-------|--------|---------|
| Chicago White Sox | baseball | mlb | 4 |
| Chicago Cubs | baseball | mlb | 16 |
| Indianapolis Colts | football | nfl | 11 |
| Indiana Pacers | basketball | nba | 15 |
| Purdue Boilermakers | basketball | mens-college-basketball | 2509 |
| Chicago Blackhawks | hockey | nhl | 4 |
| Valparaiso Beacons | volleyball | womens-college-volleyball | 2674 |
| Ball State Cardinals | volleyball | womens-college-volleyball | 2050 |

### Active game logic
A game is considered "active" if:
- **Live** — ESPN `status.type.state == "in"`, or
- **Recently completed** — `state == "post"` and the game started within the last **16 hours** (`RECENT_GAME_HOURS`). The 16-hour window covers the 12-hour intent from the spec plus a ~4-hour buffer for long games.

Scoreboard requests are batched by `(sport, league)` to minimise API calls. Events are deduplicated by ESPN event ID when today + yesterday are both fetched.

### Layout selection
| Active games | Layout |
|---|---|
| 0 | `empty` — upcoming schedule for all 8 teams |
| 1 | `single` — full-screen card |
| 2 | `split` — two equal half-screen cards |
| 3+ | `grid` — equal-width cards |

### Volleyball set-by-set linescores
When `sport == "volleyball"`, per-set scores are extracted from ESPN `linescores` on each competitor. Each set entry carries `away_score`, `home_score`, `away_winner`, and `home_winner` flags so the template can bold the winning side of each set.

### Rendering
The plugin delegates to `BasePlugin.render_image()` with `scores.html` / `scores.css`. Resolution and orientation come from `device_config`; for vertical orientation the width/height tuple is reversed before passing to the renderer.

## Tests

### Scripts

| Script | Purpose | Output |
|--------|---------|--------|
| `scripts/test_scores.py` | Live ESPN API smoke-test across 3 resolutions × 2 orientations | `/tmp/scores_test_output.png` |
| `scripts/test_scores_volleyball.py` | Mocked volleyball-specific scenarios (5 cases) | `/tmp/scores_volleyball_test.png` |
| `scripts/test_scores_layouts.py` | Mocked showcase of all 4 layouts across all sports | `/tmp/scores_layouts_showcase.png` |

### Layout showcase scenarios (`test_scores_layouts.py`)

| # | Label | Layout | What it covers |
|---|-------|--------|----------------|
| 1 | Blackhawks live – hockey | `single` | Live NHL game, full-screen card |
| 2 | Pacers won – basketball | `single` | Final NBA game, winner highlighted |
| 3 | White Sox live – baseball | `single` | Live MLB game |
| 4 | Ball State live – volleyball | `single` | Live volleyball with set-by-set scores; live set highlighted green |
| 5 | Cubs final + Pacers live | `split` | Two games, two sports simultaneously |
| 6 | Hawks + Pacers + Cubs | `grid` | Three-game grid |
| 7 | Hawks + Pacers + White Sox + Cubs | `grid` | Four-game grid; two MLB teams in one scoreboard call |
| 8 | No active games | `empty` | Upcoming schedule for all 8 teams; schedule endpoint mocked with real future dates |

### Volleyball scenarios (`test_scores_volleyball.py`)

| # | Label | Layout | What it covers |
|---|-------|--------|----------------|
| 1 | Live BSU in set 3 (2–0 sets) | `single` | Live volleyball game; 3 sets of linescores where set 3 has no winner yet |
| 2 | Final VAL won 3–1 | `single` | Completed volleyball game; 4 sets with mixed winners; `is_final` path |
| 3 | Two vball games (split) | `split` | Both tracked volleyball teams active simultaneously |
| 4 | Vball live + Cubs final (grid) | `grid` | Mixed sports — one volleyball + one MLB game; 3+ active game path |
| 5 | No active games (upcoming) | `empty` | All scoreboards empty; schedule endpoint returns `[]` so upcoming list is empty too |

### Running
```bash
PYTHONPATH=src .venv/bin/python3 scripts/test_scores_layouts.py
PYTHONPATH=src .venv/bin/python3 scripts/test_scores_volleyball.py
PYTHONPATH=src .venv/bin/python3 scripts/test_scores.py
```
Requires `chromium`, `chromium-headless-shell`, or `chrome` on `PATH`. Output is opened automatically with the default image viewer.

**macOS with Google Chrome:** `test_scores_volleyball.py` and `test_scores_layouts.py` already monkey-patch the browser finder to use `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. For `test_scores.py`, symlink Chrome into a directory on your PATH:
```bash
sudo ln -sf "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" /usr/local/bin/chrome
```

### Mock data conventions

All mocked scenarios follow the same ESPN API shape. Key things to know when adding new scenarios:

- **Scoreboard events** are keyed by `"{sport}/{league}"` in the `events_by_league` dict passed to `make_mock_get()`. Both teams in a league (e.g. CWS + CHC in `baseball/mlb`) can share a single list.
- **A game is shown** only if a competitor's `id` matches one of the `TRACKED_TEAMS` ids. Opponent teams need a different id.
- **`is_active` date check**: `"post"` games must have a `date` within the last 16 hours of wall-clock time, otherwise they are filtered out. Use `RECENT = NOW - 2h` for finals; `LIVE` for in-progress.
- **Volleyball linescores** are per-competitor, per-set. Each linescore entry needs `value`, `displayValue`, `period.number`, and `winner`. The away and home competitors carry their own separate lists; the plugin zips them by period number.
- **Schedule mock**: keyed by `"{team_id}/{sport}/{league}"`. Events must have `status.type.state == "pre"` and a future `date` or they are skipped by `_fetch_next_game`.