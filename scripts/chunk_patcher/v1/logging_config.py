# logging_config.py
import logging
from datetime import datetime
from pathlib import Path

def setup_logging(name: str = 'ADTProcessor', log_dir: str = None) -> logging.Logger:
   timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
   logger = logging.getLogger(name)
   logger.handlers = []
   logger.setLevel(logging.INFO)

   if log_dir:
       Path(log_dir).mkdir(parents=True, exist_ok=True)
       log_path = Path(log_dir) / f'adt_processor_{timestamp}.log'
   else:
       log_path = f'adt_processor_{timestamp}.log'

   formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

   file_handler = logging.FileHandler(log_path, 'w', 'utf-8')
   file_handler.setFormatter(formatter)
   file_handler.setLevel(logging.INFO)
   logger.addHandler(file_handler)

   console_handler = logging.StreamHandler()
   console_handler.setFormatter(formatter)
   console_handler.setLevel(logging.INFO)
   logger.addHandler(console_handler)

   return logger