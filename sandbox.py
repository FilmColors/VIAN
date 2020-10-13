import pysrt
from core.data.computation import ts_to_ms
path = "data/examples/paris_texas_en.srt"

codecs = ["utf-8", "iso-8859-1"]
subs = pysrt.open(path, encoding=codecs[0])
for s in subs:
    text = s.text
    start = ts_to_ms(s.start.hours, s.start.minutes, s.start.seconds, s.start.milliseconds)
    end = ts_to_ms(s.end.hours, s.end.minutes, s.end.seconds, s.end.milliseconds)