import logging
from pathlib import Path
from typing import Union

def setup_logging(output_dir: Union[str, Path], filename: str = "output.log") -> None:
    """Set up logging to both file and console for a specific processing job."""
    output_dir = Path(output_dir)
    log_file = output_dir / filename

    # Reset logger to remove any existing handlers
    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.INFO)

    # File handler - includes timestamps
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Console handler - cleaner output without timestamps
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter("%(message)s")
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    logging.info(f"Started processing. Log file: {log_file}")