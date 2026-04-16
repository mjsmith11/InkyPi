import logging
import requests
from datetime import datetime, timezone, timedelta
import pytz
from plugins.base_plugin.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

# ─── Hardcoded tracked teams ───────────────────────────────────────────────────
TRACKED_TEAMS = [
    {"name": "Chicago White Sox",   "abbreviation": "CWS", "sport": "baseball",   "league": "mlb",                     "id": "4"},
    {"name": "Chicago Cubs",        "abbreviation": "CHC", "sport": "baseball",   "league": "mlb",                     "id": "16"},
    {"name": "Indianapolis Colts",  "abbreviation": "IND", "sport": "football",   "league": "nfl",                     "id": "11"},
    {"name": "Indiana Pacers",      "abbreviation": "IND", "sport": "basketball", "league": "nba",                     "id": "15"},
    {"name": "Purdue Boilermakers", "abbreviation": "PUR", "sport": "basketball", "league": "mens-college-basketball", "id": "2509"},
    {"name": "Chicago Blackhawks",  "abbreviation": "CHI", "sport": "hockey",     "league": "nhl",                     "id": "4"},
]

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
ESPN_SCHEDULE_URL   = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}/schedule"

# Show completed games that started within this many hours ago (12h window + ~4h game buffer)
RECENT_GAME_HOURS = 16


class Scores(BasePlugin):

    def generate_image(self, settings, device_config):
        timezone_str = device_config.get_config("timezone", default="America/Chicago")
        time_format  = device_config.get_config("time_format", default="12h")
        tz  = pytz.timezone(timezone_str)
        now = datetime.now(tz)

        active_games   = self._get_active_games(now)
        upcoming_games = self._get_upcoming_games(now, tz, time_format) if not active_games else []

        n = len(active_games)
        if n == 0:
            layout = "empty"
        elif n == 1:
            layout = "single"
        elif n == 2:
            layout = "split"
        else:
            layout = "grid"

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        template_params = {
            "layout":          layout,
            "games":           active_games,
            "upcoming_games":  upcoming_games,
            "plugin_settings": {},
        }

        image = self.render_image(dimensions, "scores.html", "scores.css", template_params)
        if not image:
            raise RuntimeError("Failed to render scores image.")
        return image

    # ── Active games ───────────────────────────────────────────────────────────

    def _get_active_games(self, now):
        active = []

        by_league = {}
        for team in TRACKED_TEAMS:
            key = (team["sport"], team["league"])
            by_league.setdefault(key, []).append(team)

        for (sport, league), teams in by_league.items():
            team_id_map = {t["id"]: t for t in teams}
            events = self._fetch_scoreboard(sport, league, now)
            for event in events:
                matched = self._match_team(event, team_id_map)
                if matched and self._is_active(event):
                    active.append(self._parse_game(event, matched))

        return active

    def _fetch_scoreboard(self, sport, league, now):
        """Fetch today's and yesterday's events, deduplicated by ESPN event ID."""
        seen, events = set(), []
        url = ESPN_SCOREBOARD_URL.format(sport=sport, league=league)
        for delta in (0, -1):
            date_str = (now + timedelta(days=delta)).strftime("%Y%m%d")
            try:
                r = requests.get(url, params={"dates": date_str}, timeout=10)
                if r.status_code == 200:
                    for e in r.json().get("events", []):
                        eid = e.get("id")
                        if eid not in seen:
                            seen.add(eid)
                            events.append(e)
            except Exception as exc:
                logger.warning("Scoreboard fetch failed %s/%s %s: %s", sport, league, date_str, exc)
        return events

    def _match_team(self, event, team_id_map):
        competitors = event.get("competitions", [{}])[0].get("competitors", [])
        for c in competitors:
            if c.get("id") in team_id_map:
                return team_id_map[c["id"]]
        return None

    def _is_active(self, event):
        state = event.get("status", {}).get("type", {}).get("state", "")
        if state == "in":
            return True
        if state == "post":
            try:
                start = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                age_h = (datetime.now(timezone.utc) - start).total_seconds() / 3600
                return age_h <= RECENT_GAME_HOURS
            except Exception:
                pass
        return False

    def _parse_game(self, event, matched_team):
        comp        = event.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        stype       = event.get("status", {}).get("type", {})
        state       = stype.get("state", "post")

        away, home = {}, {}
        for c in competitors:
            t = c.get("team", {})
            entry = {
                "name":         t.get("displayName", t.get("name", "")),
                "abbreviation": t.get("abbreviation", ""),
                "color":        self._safe_color(t.get("color", "333333")),
                "logo":         t.get("logo", ""),
                "score":        c.get("score", "0"),
                "is_winner":    c.get("winner", False),
            }
            if c.get("homeAway") == "home":
                home = entry
            else:
                away = entry

        return {
            "away":         away,
            "home":         home,
            "status_label": stype.get("shortDetail", "Final"),
            "is_final":     state == "post",
            "is_live":      state == "in",
            "sport":        matched_team["sport"],
        }

    # ── Upcoming games ─────────────────────────────────────────────────────────

    def _get_upcoming_games(self, now, tz, time_format):
        upcoming = []
        for team in TRACKED_TEAMS:
            info = self._fetch_next_game(team, now, tz, time_format)
            if info:
                upcoming.append(info)
        return upcoming

    def _fetch_next_game(self, team, now, tz, time_format):
        url = ESPN_SCHEDULE_URL.format(
            sport=team["sport"], league=team["league"], team_id=team["id"]
        )
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                return None
            events = r.json().get("events", [])
        except Exception as exc:
            logger.warning("Schedule fetch failed for %s: %s", team["name"], exc)
            return None

        for event in events:
            if event.get("status", {}).get("type", {}).get("state") != "pre":
                continue
            try:
                start_utc = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                if start_utc <= datetime.now(timezone.utc):
                    continue

                local    = start_utc.astimezone(tz)
                date_str = local.strftime("%a, %b %-d")
                time_str = (
                    local.strftime("%H:%M")
                    if time_format == "24h"
                    else local.strftime("%-I:%M %p")
                )

                competitors = event.get("competitions", [{}])[0].get("competitors", [])
                our_c = next((c for c in competitors if c.get("id") == team["id"]), None)
                opp_c = next((c for c in competitors if c.get("id") != team["id"]), None)
                if not opp_c:
                    continue

                our_t = (our_c or {}).get("team", {})
                opp_t = opp_c.get("team", {})

                return {
                    "team_name":             team["name"],
                    "team_abbreviation":     team["abbreviation"],
                    "team_color":            self._safe_color(our_t.get("color", "333333")),
                    "team_logo":             our_t.get("logo", ""),
                    "opponent_abbreviation": opp_t.get("abbreviation", ""),
                    "opponent_logo":         opp_t.get("logo", ""),
                    "is_home":               (our_c.get("homeAway") == "home") if our_c else False,
                    "date_str":              date_str,
                    "time_str":              time_str,
                }
            except Exception as exc:
                logger.debug("Schedule parse error for %s: %s", team["name"], exc)

        return None

    # ── Utilities ──────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_color(hex_str):
        """Normalize a hex color string (with or without #) to #RRGGBB."""
        h = hex_str.lstrip("#").lower()
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return "#" + h[:6].zfill(6)
