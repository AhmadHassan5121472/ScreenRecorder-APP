import logging
import os


class AppLogger:
    def __init__(self, log_folder="logs", log_file="screen_recorder.log"):
        os.makedirs(log_folder, exist_ok=True)
        self.log_path = os.path.join(log_folder, log_file)
        self.logger = logging.getLogger("ScreenRecorder")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        if not self.logger.handlers:
            fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            fh = logging.FileHandler(self.log_path, encoding="utf-8")
            fh.setFormatter(fmt)
            fh.setLevel(logging.DEBUG)
            self.logger.addHandler(fh)

    def info(self, message): self.logger.info(message)
    def warning(self, message): self.logger.warning(message)
    def error(self, message): self.logger.error(message)
    def debug(self, message): self.logger.debug(message)
    def exception(self, message): self.logger.exception(message)
