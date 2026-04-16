"""
Quick test script for the scores plugin.
Usage: run from repo root with the venv active.
  PYTHONPATH=src PATH="/tmp:$PATH" .venv/bin/python3 scripts/test_scores.py
"""
import sys, os, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import requests
from unittest.mock import MagicMock
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("test_scores")

# ── Load the plugin ──────────────────────────────────────────────────────────
from plugins.plugin_registry import load_plugins, get_plugin_instance

PLUGIN_CONFIG = {"display_name": "Scores", "id": "scores", "class": "Scores", "repository": ""}
load_plugins([PLUGIN_CONFIG])
plugin = get_plugin_instance(PLUGIN_CONFIG)

# ── Mock device config ───────────────────────────────────────────────────────
RESOLUTIONS = [
    (800, 480),   # Inky Impression 7.3"
    (600, 448),   # Inky Impression 5.7"
    (640, 400),   # Inky Impression 4"
]

def make_device_config(resolution, orientation="horizontal"):
    cfg = MagicMock()
    cfg.get_resolution.return_value = list(resolution)
    def get_config(key, default=None):
        if key == "orientation": return orientation
        if key == "timezone":    return "America/Chicago"
        if key == "time_format": return "12h"
        return default
    cfg.get_config.side_effect = get_config
    return cfg

# ── Smoke-test: live API call + render ───────────────────────────────────────
settings = {}
rows = []
for resolution in RESOLUTIONS:
    for orientation in ("horizontal", "vertical"):
        logger.info("Testing %s %s ...", resolution, orientation)
        cfg = make_device_config(resolution, orientation)
        try:
            img = plugin.generate_image(settings, cfg)
            assert img is not None, "generate_image returned None"
            rows.append((resolution, orientation, img, None))
            logger.info("  OK  layout rendered, size=%s", img.size)
        except Exception as e:
            logger.error("  FAIL: %s", e)
            rows.append((resolution, orientation, None, str(e)))

# ── Show composite ───────────────────────────────────────────────────────────
successes = [(r, o, img) for r, o, img, err in rows if img]
if not successes:
    logger.error("All renders failed.")
    sys.exit(1)

max_w = max(img.width  for _, _, img in successes)
max_h = max(img.height for _, _, img in successes)
cols  = 2
grid_rows = (len(successes) + 1) // cols

composite = Image.new("RGB", (max_w * cols, max_h * grid_rows), color=(40, 40, 40))
for i, (res, ori, img) in enumerate(successes):
    # rotate vertical back so it reads correctly in the composite
    if ori == "vertical":
        img = img.rotate(-90, expand=True)
    img = img.resize((max_w, max_h), Image.LANCZOS)
    cx = (i % cols) * max_w
    cy = (i // cols) * max_h
    composite.paste(img, (cx, cy))

out_path = "/tmp/scores_test_output.png"
composite.save(out_path)
logger.info("Composite saved to %s (%dx%d, %d panels)", out_path, composite.width, composite.height, len(successes))
composite.show()
