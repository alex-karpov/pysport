import logging
import os
from datetime import datetime


class DailyFileHandler(logging.FileHandler):
    """Logging handler that writes logs to a daily file.

    Each day a new log file is created. Filenames are constructed from the
    provided `prefix`, the date in YYYYMMDD format, and the `suffix` with a
    `.log` extension. When the date changes the handler closes the current
    stream and starts writing to a new file for the new day.
    """

    def __init__(self, prefix="", suffix="", mode="a", encoding=None, delay=False):
        """Initialize the handler.

        Args:
            prefix (str): String placed before the date in the filename.
            suffix (str): String placed after the date in the filename.
            mode (str): File open mode (default: 'a').
            encoding (Optional[str]): File encoding to use.
            delay (bool): If True, file opening is deferred until the first
                call to `emit`.
        """
        self.prefix = prefix
        self.suffix = suffix
        self.current_date = datetime.now().date()
        filename = self._make_filename(self.current_date)
        super().__init__(filename, mode, encoding, delay)

    def _make_filename(self, date_obj):
        """Return a filename for the given date.

        The returned filename has the form: <prefix><YYYYMMDD><suffix>.log

        Args:
            date_obj (datetime.date): Date used to format the filename.

        Returns:
            str: The constructed filename.
        """
        return make_log_filename(prefix=self.prefix, suffix=self.suffix)

    def emit(self, record):
        """Emit a record, switching the output file if the day changed.

        This method checks the current date and, if it differs from the
        handler's stored `current_date`, updates `baseFilename`, closes the
        current stream and lets the base class handle opening the new file
        and writing the record.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        today = datetime.now().date()
        if today != self.current_date:
            self.current_date = today
            self.baseFilename = os.path.abspath(self._make_filename(today))
            if self.stream:
                self.stream.close()
                self.stream = None
        super().emit(record)


def make_log_filename(prefix="", suffix=""):
    """Return a log filename for the current date.

    The returned filename has the form: <prefix><YYYYMMDD><suffix>.log

    Args:
        prefix (str): String placed before the date in the filename.
        suffix (str): String placed after the date in the filename.

    Returns:
        str: The constructed filename.
    """
    return "{base}{date}{suffix}.log".format(
        base=prefix,
        date=datetime.now().strftime("%Y%m%d"),
        suffix=suffix,
    )
