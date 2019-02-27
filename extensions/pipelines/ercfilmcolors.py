from core.data.creation_events import segment_created_event, screenshot_created_event

@segment_created_event
def filmcolors_segment_created(segment):
    print(segment)