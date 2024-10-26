import logging

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-9s %(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)