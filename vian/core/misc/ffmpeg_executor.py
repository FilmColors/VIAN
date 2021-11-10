"""
https://stackoverflow.com/questions/7632589/getting-realtime-output-from-ffmpeg-to-be-used-in-progress-bar-pyqt4-stdout

"""

import subprocess
import re
from typing import Iterator

DUR_REGEX = re.compile(
    r"Duration: (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})"
)
TIME_REGEX = re.compile(
    r"out_time=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})"
)


def to_ms(s=None, des=None, **kwargs) -> float:
    if s:
        hour = int(s[0:2])
        minute = int(s[3:5])
        sec = int(s[6:8])
        ms = int(s[10:11])
    else:
        hour = int(kwargs.get("hour", 0))
        minute = int(kwargs.get("min", 0))
        sec = int(kwargs.get("sec", 0))
        ms = int(kwargs.get("ms", 0))

    result = (hour * 60 * 60 * 1000) + (minute * 60 * 1000) + (sec * 1000) + ms
    if des and isinstance(des, int):
        return round(result, des)
    return result


def run_ffmpeg_command(cmd: "list[str]") -> Iterator[float]:
    """
    Run an ffmpeg command, trying to capture the process output and calculate
    the duration / progress.
    Yields the progress in percent.
    """
    total_dur = None

    cmd_with_progress = [cmd[0]] + ["-progress", "-", "-nostats"] + cmd[1:]

    stderr = []

    p = subprocess.Popen(
        cmd_with_progress,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=False,
    )

    while True:
        line = p.stdout.readline().decode("utf8", errors="replace").strip()
        if line == "" and p.poll() is not None:
            break
        stderr.append(line.strip())

        if not total_dur and DUR_REGEX.search(line):
            total_dur = DUR_REGEX.search(line).groupdict()
            total_dur = to_ms(**total_dur)
            continue
        if total_dur:
            result = TIME_REGEX.search(line)
            if result:
                elapsed_time = to_ms(**result.groupdict())
                yield (elapsed_time / total_dur * 100) / 100

    if p.returncode != 0:
        raise RuntimeError(
            "Error running command {}: {}".format(cmd, str("\n".join(stderr)))
        )

    yield 1.0


def ffmpeg_convert(input, output, callback):
    for progress in run_ffmpeg_command(["ffmpeg", "-i", input, output]):
        callback(progress)