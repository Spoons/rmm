import logging


def setup_logging(name: str = __name__):
    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)  # Set the logging level

    # Create a console handler and set level to debug
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create a formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(console_handler)

    return logger
