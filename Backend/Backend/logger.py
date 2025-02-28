import json
import os
import socket
import logging
import sys
import inspect
from datetime import datetime
from Backend.settings import DEBUG


class EnhancedDateTimeEncoder(json.JSONEncoder):
    """Custom encoder for datetime objects and handling non-serializable objects."""

    def __init__(self, *args, **kwargs):
        super(EnhancedDateTimeEncoder, self).__init__(*args, **kwargs)
        self.seen = set()  # Track already seen objects to detect circular references

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif id(obj) in self.seen:
            # Return a placeholder for circular references
            return "Circular reference detected"
        else:
            self.seen.add(id(obj))
            try:
                if hasattr(obj, 'dict'):
                    return obj.dict()
                elif hasattr(obj, '__dict__'):
                    return {key: self.default(value) for key, value in obj.__dict__.items() if not key.startswith('_')}
                else:
                    return str(obj)
            except TypeError:
                return str(obj)
            except Exception as e:
                return f'Error serializing object: {str(e)}'
            finally:
                # Remove the object from the seen set to avoid false positives in subsequent serializations
                self.seen.remove(id(obj))


class CustomLogFilter(logging.Filter):
    """Custom log filter to add additional fields to log records."""

    def filter(self, record):
        record.hostname = socket.gethostbyname(socket.gethostname())
        return True


# Set up logger
logger = logging.getLogger('Backend')
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
logger.propagate = False

# Formatter for log messages
formatter = logging.Formatter("[%(asctime)s]- host:%(hostname)s level:%(levelname)s — %(message)s",
                              datefmt="%d/%b/%Y %H:%M:%S")

# Stream handler for logging to stdout
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

# Custom log filter
custom_filter = CustomLogFilter()
logger.addFilter(custom_filter)


def log(level, function, status_code=None, **kwargs):
    # Serialize additional info with the enhanced JSON encoder
    log_message = json.dumps(kwargs, cls=EnhancedDateTimeEncoder)

    # Initialize args_str outside the if block to use it later
    args_str = None
    if level >= logging.ERROR:
        frame = inspect.currentframe().f_back
        args, _, _, values = inspect.getargvalues(frame)
        args_dict = {arg: values[arg] for arg in args if arg != 'self'}
        args_str = json.dumps(args_dict, cls=EnhancedDateTimeEncoder)

    source_file = os.path.relpath(inspect.stack()[1].filename)
    frame_number = inspect.stack()[1].lineno
    status_code_str = "status_code:" + str(status_code) if status_code is not None else "status_code:N/A"

    # Construct log_details with or without args based on level
    if args_str:
        log_details = f"file:{source_file} - line_num:{frame_number} - function:{function} - {status_code_str} - args:{args_str} - message:{log_message}"
    else:
        log_details = f"file:{source_file} - line_num:{frame_number} - function:{function} - {status_code_str} - message:{log_message}"

    logger.log(level, log_details)