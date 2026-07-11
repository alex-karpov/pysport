"""TEMPORARY dev tool: render the fee report templates from a SportOrg race file.

Delete together with tests/test_team_fee_report.py when the templates are done.
"""

from __future__ import annotations

import os
import webbrowser
from typing import Any, Dict

from sportorg import config
from sportorg import settings as sportorg_settings
from sportorg.common.template import get_text_from_file
from team_extract_preview import REPO_ROOT, TEMPLATES_DIR, load_sample_race

FEE_RACE = os.path.join(REPO_ROOT, "data", "2024-01-28_relay_international_fee.json")

VARIANTS = [
    "reports/2_выписки_по_командам_взнос.html",
    "reports/2_выписки_по_командам_взнос_10процентов.html",
]


def render_fee(template_rel: str, race: Dict[str, Any]) -> str:
    """Render one fee template with the same context the report dialog uses."""
    sportorg_settings.SETTINGS.templates_path = TEMPLATES_DIR
    return get_text_from_file(
        template_rel,
        race=race,
        races=[race],
        current_race=0,
        rent_cards=[],
        selected={"persons": []},
        name=config.NAME,
        version=str(config.VERSION),
    )


def main() -> None:
    race = load_sample_race(FEE_RACE)
    for rel in VARIANTS:
        path = os.path.join(TEMPLATES_DIR, rel.replace("/", os.sep))
        if not os.path.exists(path):
            continue
        html = render_fee(rel, race)
        out = os.path.join(
            REPO_ROOT, os.path.basename(rel).replace(".html", "_preview.html")
        )
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print("Wrote", out)
        webbrowser.open("file:///" + out.replace("\\", "/") + "?selftest")


if __name__ == "__main__":
    main()
