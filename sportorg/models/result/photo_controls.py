import csv
import logging
from typing import Dict, List

from sportorg.common.otime import OTime
from sportorg.models.memory import ResultSportident, Split

# A photo control mark is added with its time set to the result start time.
# Two marks within this tolerance of the start time are treated as the same
# already-loaded photo mark (absorbs OTime rounding).
DEDUP_TOLERANCE_MSEC = 1000


def is_photo_mark(split: Split, start_time: OTime) -> bool:
    """True when a split is a photo control: its time sits at the start time.

    Marks created by ``append_photo_controls`` carry the result start time, so
    this is the single convention used both to deduplicate on merge and to
    recognise photo marks elsewhere (e.g. split printout). ``DEDUP_TOLERANCE_MSEC``
    absorbs OTime rounding.
    """
    return abs(split.time.to_msec() - start_time.to_msec()) <= DEDUP_TOLERANCE_MSEC


def load_team_controls(csv_path: str) -> Dict[int, List[str]]:
    """Parse a ``;``-delimited photo-controls CSV into ``{team_bib: [code, ...]}``.

    Column index 1 holds the team bib, column index 2 holds the control code.
    """
    team_controls: Dict[int, List[str]] = {}
    with open(csv_path, "r") as csv_file:
        reader = csv.reader(csv_file, delimiter=";")
        for row in reader:
            if len(row) < 3:
                continue
            try:
                team_bib = int(row[1])
            except (ValueError, IndexError):
                continue
            team_controls.setdefault(team_bib, []).append(row[2])
    return team_controls


def append_photo_controls(
    result: ResultSportident, team_controls: Dict[int, List[str]]
) -> int:
    """Merge a team's photo controls into ``result`` as extra splits.

    The team bib is ``result.person.bib // 10``. A photo mark for code ``C`` is
    added only when no existing split has the same code within
    ``DEDUP_TOLERANCE_MSEC`` of the start time, so re-running is idempotent and a
    real chip punch (with a mid-race time) does not suppress the photo mark.
    Returns the number of marks added.
    """
    if not (result.person and result.person.bib):
        logging.warning(
            "Cannot append photo controls for sicard %s, no bib number for result",
            result.card_number,
        )
        return 0

    team_bib = result.person.bib // 10
    codes = team_controls.get(team_bib, [])
    if not codes:
        return 0

    start_time = result.get_start_time()

    def already_present(code: str) -> bool:
        for split in result.splits:
            if split.code == code and is_photo_mark(split, start_time):
                return True
        return False

    new_splits = []
    for code in codes:
        if already_present(code):
            continue
        split = Split()
        split.code = code
        split.time = start_time
        new_splits.append(split)

    if new_splits:
        result.splits = new_splits + result.splits

    return len(new_splits)
