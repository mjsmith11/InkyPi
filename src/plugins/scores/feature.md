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

Test script: `scripts/test_scores_volleyball.py`

Runs five scenarios by mocking `requests.get` and rendering the plugin directly to PNG, then stacks all outputs into a single composite image saved to `/tmp/scores_volleyball_test.png`.

### Scenarios

| # | Label | Layout | What it covers |
|---|-------|--------|----------------|
| 1 | Live BSU in set 3 (2–0 sets) | `single` | Live volleyball game; 3 sets of linescores where set 3 has no winner yet |
| 2 | Final VAL won 3–1 | `single` | Completed volleyball game; 4 sets with mixed winners; `is_final` path |
| 3 | Two vball games (split) | `split` | Both tracked volleyball teams active simultaneously |
| 4 | Vball live + Cubs final (grid) | `grid` | Mixed sports — one volleyball + one MLB game; 3+ active game path |
| 5 | No active games (upcoming) | `empty` | All scoreboards empty; schedule endpoint returns `[]` so upcoming list is empty too |

### Running
```bash
python scripts/test_scores_volleyball.py
```
Requires Chrome/Chromium on the host (path is hardcoded to the macOS Google Chrome app bundle in the script). Output is opened automatically with the default image viewer.