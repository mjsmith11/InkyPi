"""
Layout showcase for the scores plugin – all possible screen configurations.

Scenarios:
  1. Single – Blackhawks live (hockey)
  2. Single – Pacers won (basketball)
  3. Single – White Sox live (baseball)
  4. Split  – Cubs final + Pacers live (2 games)
  5. Grid   – 3 simultaneous games
  6. Grid   – 4 simultaneous games
  7. Empty  – no active games, upcoming schedule shown
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw, ImageFont
from plugins.plugin_registry import load_plugins, get_plugin_instance
from utils.image_utils import resize_image
import utils.image_utils as _iu

_iu._find_chromium_binary = lambda: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

plugin_cfg = {"id": "scores", "class": "Scores"}
load_plugins([plugin_cfg])
plugin = get_plugin_instance(plugin_cfg)

RESOLUTION = (800, 480)

# ── Helpers ───────────────────────────────────────────────────────────────────

def mock_device_config(resolution=RESOLUTION, orientation="horizontal"):
    m = MagicMock()
    m.get_resolution.return_value = list(resolution)
    def _cfg(key, default=None):
        return {"orientation": orientation, "timezone": "America/Chicago", "time_format": "12h"}.get(key, default)
    m.get_config.side_effect = _cfg
    return m

def make_competitor(team_id, home_away, score, winner, name, abbr, color, logo, linescores=None):
    return {
        "id": str(team_id), "homeAway": home_away,
        "score": str(score), "winner": winner,
        "team": {"id": str(team_id), "displayName": name, "abbreviation": abbr, "color": color, "logo": logo},
        "linescores": linescores or [],
    }

def make_linescore(period, val, won):
    return {"value": val, "displayValue": str(val), "period": {"number": period}, "winner": won}

def make_event(eid, date, state, detail, away, home):
    return {
        "id": str(eid), "date": date,
        "status": {"type": {"state": state, "shortDetail": detail}},
        "competitions": [{"competitors": [away, home]}],
    }

def c(t, home_away, score, winner):
    return make_competitor(t["id"], home_away, score, winner, t["name"], t["abbr"], t["color"], t["logo"])

def e(eid, date, state, detail, away_t, as_, aw, home_t, hs, hw):
    return make_event(eid, date, state, detail, c(away_t, "away", as_, aw), c(home_t, "home", hs, hw))

# ── Time anchors ──────────────────────────────────────────────────────────────

NOW    = datetime.now(timezone.utc)
RECENT = (NOW - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
LIVE   = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
FUTURE = (NOW + timedelta(days=2, hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Teams (tracked) ───────────────────────────────────────────────────────────

T = {
    "cws": {"id": "4",    "name": "Chicago White Sox",   "abbr": "CWS", "color": "000000", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/cws.png"},
    "chc": {"id": "16",   "name": "Chicago Cubs",        "abbr": "CHC", "color": "0E3386", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/chc.png"},
    "ind": {"id": "11",   "name": "Indianapolis Colts",  "abbr": "IND", "color": "003B75", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/ind.png"},
    "pac": {"id": "15",   "name": "Indiana Pacers",      "abbr": "IND", "color": "002D62", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/ind.png"},
    "pur": {"id": "2509", "name": "Purdue Boilermakers", "abbr": "PUR", "color": "CEB888", "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/2509.png"},
    "chi": {"id": "4",    "name": "Chicago Blackhawks",  "abbr": "CHI", "color": "CF0A2C", "logo": "https://a.espncdn.com/i/teamlogos/nhl/500/chi.png"},
    "val": {"id": "2674", "name": "Valparaiso Beacons",  "abbr": "VAL", "color": "5B2D8E", "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/2674.png"},
    "bsu": {"id": "2050", "name": "Ball State Cardinals","abbr": "BSU", "color": "CC0000", "logo": "https://a.espncdn.com/i/teamlogos/ncaa/500/2050.png"},
}

# ── Opponents (not tracked) ───────────────────────────────────────────────────

O = {
    "det": {"id": "5001", "name": "Detroit Tigers",       "abbr": "DET", "color": "0C2340", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/det.png"},
    "mil": {"id": "5002", "name": "Milwaukee Brewers",    "abbr": "MIL", "color": "12284B", "logo": "https://a.espncdn.com/i/teamlogos/mlb/500/mil.png"},
    "jax": {"id": "5003", "name": "Jacksonville Jaguars", "abbr": "JAX", "color": "006778", "logo": "https://a.espncdn.com/i/teamlogos/nfl/500/jax.png"},
    "mia": {"id": "5004", "name": "Miami Heat",           "abbr": "MIA", "color": "98002E", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/mia.png"},
    "nyk": {"id": "5005", "name": "New York Knicks",      "abbr": "NYK", "color": "006BB6", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/nyk.png"},
    "col": {"id": "5006", "name": "Colorado Avalanche",   "abbr": "COL", "color": "6F263D", "logo": "https://a.espncdn.com/i/teamlogos/nhl/500/col.png"},
    "min": {"id": "5007", "name": "Minnesota Wild",       "abbr": "MIN", "color": "154734", "logo": "https://a.espncdn.com/i/teamlogos/nhl/500/min.png"},
    "bos": {"id": "5008", "name": "Boston Celtics",       "abbr": "BOS", "color": "007A33", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/bos.png"},
}

# ── Scenario data ─────────────────────────────────────────────────────────────

def single_hockey():
    ev = e(1, LIVE, "in", "3rd 12:34", T["chi"], 3, False, O["col"], 2, False)
    return {"hockey/nhl": [ev]}

def single_basketball():
    ev = e(2, RECENT, "post", "Final", O["mia"], 108, False, T["pac"], 117, True)
    return {"basketball/nba": [ev]}

def single_baseball():
    ev = e(3, LIVE, "in", "Bot 7th", T["cws"], 4, False, O["det"], 3, False)
    return {"baseball/mlb": [ev]}

def single_volleyball():
    """Ball State live in set 3, leading 2-0 in sets."""
    NIU_LOGO = "https://a.espncdn.com/i/teamlogos/ncaa/500/2459.png"
    bsu = T["bsu"]
    away = make_competitor(bsu["id"], "away", 2, False, bsu["name"], bsu["abbr"], bsu["color"], bsu["logo"], [
        make_linescore(1, 25, True),
        make_linescore(2, 25, True),
        make_linescore(3, 14, False),
    ])
    home = make_competitor("9999", "home", 0, False, "Northern Illinois Huskies", "NIU", "CC0000", NIU_LOGO, [
        make_linescore(1, 18, False),
        make_linescore(2, 20, False),
        make_linescore(3,  9, False),
    ])
    ev = make_event(20, LIVE, "in", "Set 3", away, home)
    return {"volleyball/womens-college-volleyball": [ev]}

def split_two_games():
    cubs   = e(4, RECENT, "post", "Final",   O["mil"], 2, False, T["chc"], 5, True)
    pacers = e(5, LIVE,   "in",   "Q3 4:22", T["pac"], 78, False, O["nyk"], 71, False)
    return {"baseball/mlb": [cubs], "basketball/nba": [pacers]}

def grid_three_games():
    hawks  = e(6, LIVE,   "in",   "2nd 8:14", T["chi"], 1, False, O["col"], 1, False)
    pacers = e(7, RECENT, "post", "Final",     O["mia"], 104, False, T["pac"], 111, True)
    cubs   = e(8, LIVE,   "in",   "Top 5th",  O["mil"], 1, False, T["chc"], 2, False)
    return {"hockey/nhl": [hawks], "basketball/nba": [pacers], "baseball/mlb": [cubs]}

def grid_four_games():
    hawks  = e(9,  LIVE,   "in",   "OT 1:45", T["chi"], 3, False, O["col"], 3, False)
    pacers = e(10, LIVE,   "in",   "Q4 0:58", T["pac"], 101, False, O["nyk"], 99, False)
    cws    = e(11, RECENT, "post", "Final",    T["cws"], 7, True,  O["det"], 5, False)
    chc    = e(12, LIVE,   "in",   "Bot 8th",  O["mil"], 3, False, T["chc"], 4, False)
    return {"hockey/nhl": [hawks], "basketball/nba": [pacers], "baseball/mlb": [cws, chc]}

def empty_upcoming():
    return {}

# ── Mock requests.get (scoreboard + schedule) ─────────────────────────────────

def make_upcoming_event(team, opp, is_home, date_str):
    our_id, opp_id = team["id"], opp["id"]
    our_comp = {"id": our_id, "homeAway": "home" if is_home else "away", "score": "0", "winner": False,
                "team": {"id": our_id, "displayName": team["name"], "abbreviation": team["abbr"],
                         "color": team["color"], "logo": team["logo"]}, "linescores": []}
    opp_comp = {"id": opp_id, "homeAway": "away" if is_home else "home", "score": "0", "winner": False,
                "team": {"id": opp_id, "displayName": opp["name"], "abbreviation": opp["abbr"],
                         "color": opp["color"], "logo": opp["logo"]}, "linescores": []}
    return {"id": f"up_{our_id}", "date": date_str,
            "status": {"type": {"state": "pre", "shortDetail": "7:05 PM CT"}},
            "competitions": [{"competitors": [our_comp, opp_comp]}]}

SCHEDULE = {
    "4/baseball/mlb":    [make_upcoming_event(T["cws"], O["det"], True,  FUTURE)],
    "16/baseball/mlb":   [make_upcoming_event(T["chc"], O["mil"], False, FUTURE)],
    "11/football/nfl":   [make_upcoming_event(T["ind"], O["jax"], True,  FUTURE)],
    "15/basketball/nba": [make_upcoming_event(T["pac"], O["mia"], False, FUTURE)],
    "2509/basketball/mens-college-basketball": [],
    "4/hockey/nhl":      [make_upcoming_event(T["chi"], O["min"], True,  FUTURE)],
    "2674/volleyball/womens-college-volleyball": [],
    "2050/volleyball/womens-college-volleyball": [],
}

def make_mock_get(events_by_league):
    def _mock_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        parts = url.rstrip("/").split("/")
        try:
            si = parts.index("sports")
            sport, league = parts[si + 1], parts[si + 2]
        except (ValueError, IndexError):
            sport = league = ""

        if "schedule" in url:
            try:
                ti = parts.index("teams")
                team_id = parts[ti + 1]
            except (ValueError, IndexError):
                team_id = ""
            resp.json.return_value = {"events": SCHEDULE.get(f"{team_id}/{sport}/{league}", [])}
        else:
            resp.json.return_value = {"events": events_by_league.get(f"{sport}/{league}", [])}
        return resp
    return _mock_get

# ── Render ────────────────────────────────────────────────────────────────────

def render(label, events_by_league):
    with patch("plugins.scores.scores.requests.get", side_effect=make_mock_get(events_by_league)):
        img = plugin.generate_image({}, mock_device_config())
    return resize_image(img, RESOLUTION, []), label

scenarios = [
    render("Single  │ Blackhawks live – hockey",             single_hockey()),
    render("Single  │ Pacers won – basketball",              single_basketball()),
    render("Single  │ White Sox live – baseball",            single_baseball()),
    render("Single  │ Ball State live – volleyball",         single_volleyball()),
    render("Split   │ Cubs final + Pacers live",             split_two_games()),
    render("Grid 3  │ Hawks + Pacers + Cubs",                grid_three_games()),
    render("Grid 4  │ Hawks + Pacers + White Sox + Cubs",    grid_four_games()),
    render("Empty   │ No active games – upcoming schedule",  empty_upcoming()),
]

# ── Composite ─────────────────────────────────────────────────────────────────

W, H = RESOLUTION
label_h = 32
composite = Image.new("RGB", (W, (H + label_h) * len(scenarios)), color="#cccccc")
draw = ImageDraw.Draw(composite)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 17)
except Exception:
    font = ImageFont.load_default()

y = 0
for img, label in scenarios:
    draw.rectangle([0, y, W, y + label_h], fill="#1e293b")
    draw.text((10, y + 7), label, fill="#f8fafc", font=font)
    composite.paste(img, (0, y + label_h))
    y += H + label_h

out_path = "/tmp/scores_layouts_showcase.png"
composite.save(out_path)
print(f"Saved → {out_path}")
composite.show()
