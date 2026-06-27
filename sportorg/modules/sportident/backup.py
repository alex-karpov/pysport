import logging
import sys
from multiprocessing import Process

from sportorg.common.fake_std import FakeStd
from sportorg.config import NAME, log_dir
from sportorg.logging import make_log_filename
from sportorg.utils.time import time_to_hhmmss


class BackupProcess(Process):
    def __init__(self, text):
        super().__init__()
        self.data = text

    def run(self):
        try:
            sys.stdout = FakeStd()
            sys.stderr = FakeStd()
            log_filename = make_log_filename(prefix=NAME.lower(), suffix="sportident")
            with open(log_dir(log_filename), "a") as f:
                f.write(self.data)
        except Exception as e:
            logging.error(str(e))


def backup_data(card_data):
    text = "start\n{}\n{}\n{}\n".format(
        card_data["card_number"],
        time_to_hhmmss(card_data["start"]) if "start" in card_data else "",
        time_to_hhmmss(card_data["finish"]) if "finish" in card_data else "",
    )
    text += "split_start\n"
    for i in range(len(card_data["punches"])):
        text += "{} {}\n".format(
            card_data["punches"][i][0], time_to_hhmmss(card_data["punches"][i][1])
        )

    text += "split_end\n"
    text += "end\n"

    BackupProcess(text).start()
