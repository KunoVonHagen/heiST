from typing import Any

def launch_timing_logger(start_time: float, tag: str, challenge_template_id: int | None = None, user_id: int | None = None, logfile_path: str = "/var/log/ctf-challenger-launch_timing.log", **kwargs: Any) -> None:
    """Log the timing of a challenge launch to a log file."""

    import time
    import datetime

    end_time: float = time.time()

    log_message: str = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    log_message += f" | {tag}"

    if user_id is not None:
        log_message += f" | User ID: {user_id}"

    if challenge_template_id is not None:
        log_message += f" | Challenge Template ID: {challenge_template_id}"

    log_message += f" | Start Time: {datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}"
    log_message += f" | End Time: {datetime.datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}"
    log_message += f" | Duration: {end_time - start_time:.2f} seconds"

    for key, value in kwargs.items():
        log_message += f" | {key}: {value}"

    with open(logfile_path, "a") as logfile:
        logfile.write(log_message + "\n")
