import logging
import colorlog


class ColorfulFormatter(logging.Formatter):
    def format(self, record):
        # log_fmt = "%(log_color)s%(levelname)-5s %(log_color)s%(message)s"
        log_fmt = '%(asctime)s - %(log_color)s%(levelname)s - %(message)s"'
        colors = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        }
        formatter = colorlog.ColoredFormatter(log_fmt, log_colors=colors)
        return formatter.format(record)


def configure_logging(log_level, log_file):
    log_format = "%(asctime)s - %(levelname)s - %(message)s"

    # Create a file handler with colorful formatter
    file_handler = logging.FileHandler(log_file)
    file_formatter = ColorfulFormatter(log_format)
    file_handler.setFormatter(file_formatter)

    # Create a stream handler with colorful formatter
    stream_handler = logging.StreamHandler()
    stream_formatter = ColorfulFormatter(log_format)
    stream_handler.setFormatter(stream_formatter)

    # Add both handlers to the logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
