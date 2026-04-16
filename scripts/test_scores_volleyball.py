"""
Test script for scores plugin – volleyball rendering.
Mocks ESPN API to cover:
  1. Single live volleyball game (Ball State in set 3)
  2. Single completed volleyball game (Valparaiso won 3-1)
  3. Two volleyball games simultaneously (split layout)
  4. Volleyball + another sport (grid layout)
  5. No active games – upcoming schedule (empty layout)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
from unittest.mock import patch, MagicMock
from PIL import Image
from plugins.plugin_registry import load_plugins, get_plugin_instance
from utils.image_utils import resize_image, change_orientation
import utils.image_utils as _iu

# Point the browser finder at the macOS Google Chrome app bundle
_iu._find_chromium_binary = lambda: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# ── Plugin bootstrap ──────────────────────────────────────────────────────────
plugin_cfg = {"id": "scores", "class": "Scores"}
load_plugins([plugin_cfg])
plugin = get_plugin_instance(plugin_cfg)

# ── Helpers ───────────────────────────────────────────────────────────────────
def mock_device_config(resolution=(800, 480), orientation="horizontal"):
    m = MagicMock()
    m.get_resolution.return_value = list(resolution)
    def _get_config(key, default=None):
        if key == "orientation": return orientation
        if key == "timezone":    return "America/Chicago"
        if key == "time_format": return "12h"
        return default
    m.get_config.side_effect = _get_config
    return m

def make_competitor(team_id, home_away, score, winner, team_name, abbr, color, logo, linescores=None):
    return {
        "id": str(team_id),
        "homeAway": home_away,
        "score": str(score),
        "winner": winner,
        "team": {
            "id": str(team_id),
            "displayName": team_name,
            "abbreviation": abbr,
            "color": color,
            "logo": logo,
        },
        "linescores": linescores or [],
    }

def make_linescore(period, away_val, home_val, away_winner, home_winner):
    """Return (away_ls, home_ls) linescore entries for a single set."""
    return (
        {"value": away_val, "displayValue": str(away_val),
         "period": {"number": period}, "winner": away_winner},
        {"value": home_val, "displayValue": str(home_val),
         "period": {"number": period}, "winner": home_winner},
    )

def make_event(event_id, date, state, short_detail, away_comp, home_comp):
    return {
        "id": str(event_id),
        "date": date,
        "status": {
            "type": {
                "state": state,
                "shortDetail": short_detail,
            }
        },
        "competitions": [{
            "competitors": [away_comp, home_comp],
        }],
    }

# ── Volleyball logo URLs (ESPN CDN) ───────────────────────────────────────────
BSU_LOGO  = "https://a.espncdn.com/i/teamlogos/ncaa/500/2050.png"
VAL_LOGO  = "https://a.espncdn.com/i/teamlogos/ncaa/500/2674.png"
NIU_LOGO  = "https://a.espncdn.com/i/teamlogos/ncaa/500/2459.png"
MVC_LOGO  = "https://a.espncdn.com/i/teamlogos/ncaa/500/2449.png"   # Illinois State
CHW_LOGO  = "https://a.espncdn.com/i/teamlogos/mlb/500/cws.png"
CHC_LOGO  = "https://a.espncdn.com/i/teamlogos/mlb/500/chc.png"

# ── Scenario builders ─────────────────────────────────────────────────────────

def scenario_live_bsu():
    """Ball State live in set 3 (leading 2-0 in sets)."""
    s1a, s1h = make_linescore(1, 25, 18, True,  False)
    s2a, s2h = make_linescore(2, 25, 20, True,  False)
    s3a, s3h = make_linescore(3, 14,  9, False, False)   # live, no winner yet
    away = make_competitor(2050, "away", 2, False, "Ball State Cardinals", "BSU",
                           "CC0000", BSU_LOGO, [s1a, s2a, s3a])
    home = make_competitor(9999, "home", 0, False, "Northern Illinois Huskies", "NIU",
                           "CC0000", NIU_LOGO, [s1h, s2h, s3h])
    event = make_event(1001, "2026-04-16T18:00:00Z", "in", "Set 3", away, home)
    return {"volleyball/womens-college-volleyball": [event]}

def scenario_final_val():
    """Valparaiso completed game, won 3-1."""
    s1a, s1h = make_linescore(1, 25, 22, True,  False)
    s2a, s2h = make_linescore(2, 21, 25, False, True)
    s3a, s3h = make_linescore(3, 25, 19, True,  False)
    s4a, s4h = make_linescore(4, 25, 17, True,  False)
    away = make_competitor(2674, "away", 3, True,  "Valparaiso Beacons",     "VAL",
                           "5B2D8E", VAL_LOGO, [s1a, s2a, s3a, s4a])
    home = make_competitor(8888, "home", 1, False, "Illinois State Redbirds", "ILST",
                           "CC0000", MVC_LOGO, [s1h, s2h, s3h, s4h])
    event = make_event(1002, "2026-04-16T16:00:00Z", "post", "Final", away, home)
    return {"volleyball/womens-college-volleyball": [event]}

def scenario_two_vball():
    """Both volleyball games active at the same time (split layout)."""
    # BSU live set 2
    s1a, s1h = make_linescore(1, 25, 21, True, False)
    s2a, s2h = make_linescore(2, 11,  8, False, False)
    bsu_away = make_competitor(2050, "away", 1, False, "Ball State Cardinals", "BSU",
                               "CC0000", BSU_LOGO, [s1a, s2a])
    bsu_home = make_competitor(9999, "home", 0, False, "Northern Illinois Huskies", "NIU",
                               "CC0000", NIU_LOGO, [s1h, s2h])
    bsu_event = make_event(1003, "2026-04-16T18:00:00Z", "in", "Set 2", bsu_away, bsu_home)

    # VAL live set 1
    v1a, v1h = make_linescore(1, 17, 14, False, False)
    val_away = make_competitor(2674, "away", 0, False, "Valparaiso Beacons", "VAL",
                               "5B2D8E", VAL_LOGO, [v1a])
    val_home = make_competitor(8888, "home", 0, False, "Illinois State Redbirds", "ILST",
                               "CC0000", MVC_LOGO, [v1h])
    val_event = make_event(1004, "2026-04-16T18:30:00Z", "in", "Set 1", val_away, val_home)

    return {"volleyball/womens-college-volleyball": [bsu_event, val_event]}

def scenario_vball_plus_baseball():
    """One volleyball (live) + one MLB game (Cubs final) → grid layout."""
    s1a, s1h = make_linescore(1, 25, 22, True, False)
    s2a, s2h = make_linescore(2, 18, 12, False, False)
    vball_away = make_competitor(2050, "away", 1, False, "Ball State Cardinals", "BSU",
                                 "CC0000", BSU_LOGO, [s1a, s2a])
    vball_home = make_competitor(9999, "home", 0, False, "Northern Illinois Huskies", "NIU",
                                 "CC0000", NIU_LOGO, [s1h, s2h])
    vball_event = make_event(1005, "2026-04-16T18:00:00Z", "in", "Set 2", vball_away, vball_home)

    cubs_away = make_competitor(16, "away", 5, True,  "Chicago Cubs",         "CHC", "0E3386", CHC_LOGO)
    cubs_home = make_competitor(7777, "home", 3, False, "Cincinnati Reds",     "CIN", "C6011F",
                                "https://a.espncdn.com/i/teamlogos/mlb/500/cin.png")
    cubs_event = make_event(1006, "2026-04-16T14:00:00Z", "post", "Final", cubs_away, cubs_home)

    return {
        "volleyball/womens-college-volleyball": [vball_event],
        "baseball/mlb": [cubs_event],
    }

def scenario_no_games():
    """No active games – upcoming schedule shown."""
    return {}

# ── Mock requests.get ─────────────────────────────────────────────────────────
def make_mock_get(events_by_league):
    def _mock_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        # derive key from URL: .../sports/{sport}/{league}/...
        parts = url.rstrip("/").split("/")
        try:
            sports_idx = parts.index("sports")
            sport  = parts[sports_idx + 1]
            league = parts[sports_idx + 2]
        except (ValueError, IndexError):
            sport = league = ""

        key = f"{sport}/{league}"
        if "schedule" in url:
            resp.json.return_value = {"events": []}
        else:
            resp.json.return_value = {"events": events_by_league.get(key, [])}
        return resp
    return _mock_get

# ── Render one scenario ───────────────────────────────────────────────────────
RESOLUTION = (800, 480)

def render_scenario(label, events_by_league):
    mock_get = make_mock_get(events_by_league)
    dev = mock_device_config(RESOLUTION, "horizontal")
    with patch("plugins.scores.scores.requests.get", side_effect=mock_get):
        img = plugin.generate_image({}, dev)
    img = resize_image(img, RESOLUTION, plugin_cfg.get("image_settings", []))
    return img, label

# ── Run all scenarios ─────────────────────────────────────────────────────────
scenarios = [
    render_scenario("Live BSU in set 3 (2–0 sets)",       scenario_live_bsu()),
    render_scenario("Final VAL won 3–1",                  scenario_final_val()),
    render_scenario("Two vball games (split)",            scenario_two_vball()),
    render_scenario("Vball live + Cubs final (grid)",     scenario_vball_plus_baseball()),
    render_scenario("No active games (upcoming)",         scenario_no_games()),
]

# Stack vertically with labels
W, H = RESOLUTION
label_h = 30
total_h = (H + label_h) * len(scenarios)
composite = Image.new("RGB", (W, total_h), color="#222222")

from PIL import ImageDraw, ImageFont
draw = ImageDraw.Draw(composite)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
except Exception:
    font = ImageFont.load_default()

y = 0
for img, label in scenarios:
    draw.rectangle([0, y, W, y + label_h], fill="#333333")
    draw.text((10, y + 6), label, fill="#ffffff", font=font)
    composite.paste(img, (0, y + label_h))
    y += H + label_h

out_path = "/tmp/scores_volleyball_test.png"
composite.save(out_path)
print(f"Saved → {out_path}")
composite.show()
