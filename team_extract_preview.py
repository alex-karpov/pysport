"""TEMPORARY dev tool: render the team-extracts report from a SportOrg race file.

Delete together with tests/test_team_extract_report.py when the template is done.
"""

from __future__ import annotations

import os
import webbrowser
from typing import Any, Dict

from sportorg import config
from sportorg import settings as sportorg_settings
from sportorg.common.template import get_text_from_file
from sportorg.models.memory import Race, new_event, races, set_current_race_index
from sportorg.modules.backup.json import get_races_from_file

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "docs", "templates")
TEMPLATE_REL = "reports/2_выписки_по_командам_регистрация.html"
SAMPLE_RACE = os.path.join(REPO_ROOT, "data", "2024-01-28_relay_international.json")


def load_sample_race(path: str = SAMPLE_RACE) -> Dict[str, Any]:
    """Load a SportOrg race file via the official deserializer; return its dict."""
    new_event([Race()])
    with open(path, encoding="utf-8") as f:
        event, current = get_races_from_file(f)
    new_event(event)
    set_current_race_index(current)
    return races()[current].to_dict()


def render_report(race: Dict[str, Any]) -> str:
    """Render the report template with the same context the report dialog uses."""
    sportorg_settings.SETTINGS.templates_path = TEMPLATES_DIR
    return get_text_from_file(
        TEMPLATE_REL,
        race=race,
        races=[race],
        current_race=0,
        rent_cards=[],
        selected={"persons": []},
        name=config.NAME,
        version=str(config.VERSION),
    )


def main() -> None:
    race = load_sample_race()
    html = render_report(race)
    out = os.path.join(REPO_ROOT, "team_extract_preview.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote", out)
    webbrowser.open("file:///" + out.replace("\\", "/") + "?selftest")


if __name__ == "__main__":
    main()
