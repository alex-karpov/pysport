from dataclasses import dataclass

from sportorg.common.otime import OTime
from sportorg.models.memory import Person, Result


class PoolTimeConverter:
    @staticmethod
    def otime_to_input(otime: OTime) -> int:
        if otime:
            return (
                otime.hour * 1000000
                + otime.minute * 10000
                + otime.sec * 100
                + otime.msec // 10
            )
        return 0

    @staticmethod
    def inout_to_otime(input_value: int) -> OTime:
        if input_value:
            hour = input_value // 1000000
            minute = (input_value % 1000000) // 10000
            sec = (input_value % 10000) // 100
            msec = (input_value % 100) * 10
            return OTime(hour=hour, minute=minute, sec=sec, msec=msec)
        return OTime()

    @staticmethod
    def input_to_str(input_value: int) -> str:
        if input_value:
            otime = PoolTimeConverter.inout_to_otime(input_value)
            minute = otime.hour * 60 + otime.minute
            sec = otime.sec
            hundreds = otime.msec // 10
            return f"{minute:02}:{sec:02}.{hundreds:02}"
        return "00:00.00"


@dataclass
class Competitor:
    bib: int = 0
    person: Person = None
    result: Result = None
    result_input: int = 0
