import objc
from Foundation import NSDate
from EventKit import EKEventStore, EKEvent
import threading
from datetime import datetime, timedelta, time
from calendar_utils import read_habits_from_csv, find_slot_for_habit

def get_event_store():
    return EKEventStore.alloc().init()

def request_access(event_store):
    access_granted = {"granted": False}
    finished = threading.Event()

    def completion(granted, error):
        access_granted["granted"] = granted
        finished.set()

    event_store.requestAccessToEntityType_completion_(0, completion)
    finished.wait()  # Wait for the completion handler

    if not access_granted["granted"]:
        raise PermissionError("Calendar access not granted.")

def get_calendar_by_name(event_store, calendar_name):
    calendars = event_store.calendarsForEntityType_(0)
    for calendar in calendars:
        if calendar.title() == calendar_name:
            return calendar
    return None

def add_event_to_calendar(event_store, calendar_name, title, start_date, end_date, tag="[AUTO-HABIT]"):
    calendar = get_calendar_by_name(event_store, calendar_name)
    if calendar is None:
        raise ValueError(f"Calendar '{calendar_name}' not found.")
    event = EKEvent.eventWithEventStore_(event_store)
    event.setTitle_(title)  # No tag in title
    event.setStartDate_(NSDate.dateWithTimeIntervalSince1970_(start_date.timestamp()))
    event.setEndDate_(NSDate.dateWithTimeIntervalSince1970_(end_date.timestamp()))
    event.setCalendar_(calendar)
    event.setNotes_(tag)  # Tag goes in notes
    try:
        event_store.saveEvent_span_error_(event, 0, None)
    except Exception as e:
        raise RuntimeError(f"Failed to save event: {e}")

def fetch_events_for_today(event_store, calendar_name):
    calendar = get_calendar_by_name(event_store, calendar_name)
    if calendar is None:
        raise ValueError(f"Calendar '{calendar_name}' not found.")
    now = datetime.now()
    start_of_day = datetime.combine(now.date(), time(0, 0))
    end_of_day = datetime.combine(now.date(), time(23, 59))
    start_nsdate = NSDate.dateWithTimeIntervalSince1970_(start_of_day.timestamp())
    end_nsdate = NSDate.dateWithTimeIntervalSince1970_(end_of_day.timestamp())
    predicate = event_store.predicateForEventsWithStartDate_endDate_calendars_(
        start_nsdate, end_nsdate, [calendar]
    )
    events = event_store.eventsMatchingPredicate_(predicate)
    # Convert to Python datetimes and sort
    busy_times = sorted(
        [(e.startDate().timeIntervalSince1970(), e.endDate().timeIntervalSince1970()) for e in events],
        key=lambda x: x[0]
    )
    return busy_times

def find_free_slots(busy_times, day_start, day_end, min_duration_minutes=30):
    free_slots = []
    min_duration = min_duration_minutes * 60  # seconds
    current = day_start
    for start, end in busy_times:
        if start - current >= min_duration:
            free_slots.append((current, start))
        current = max(current, end)
    if day_end - current >= min_duration:
        free_slots.append((current, day_end))
    return [(datetime.fromtimestamp(s), datetime.fromtimestamp(e)) for s, e in free_slots]

def main():
    calendar_name = ""
    event_store = get_event_store()
    request_access(event_store)
    habits = read_habits_from_csv("../habits.csv")
    today = datetime.now().date()
    busy_times = fetch_events_for_today(event_store, calendar_name)
    start_of_day = datetime.combine(today, time(0, 0)).timestamp()
    end_of_day = datetime.combine(today, time(23, 59)).timestamp()
    free_slots = find_free_slots(busy_times, start_of_day, end_of_day, min_duration_minutes=15)
    print("Free slots today:")
    for start, end in free_slots:
        print(f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}")
    for habit in habits:
        slot_start, slot_end = find_slot_for_habit(free_slots, habit, today)
        if slot_start and slot_end:
            print(f"Scheduling '{habit['habit_name']}' at {slot_start.strftime('%H:%M')}")
            # Buffer before
            buffer_minutes = habit.get("buffer_minutes", 0)
            if buffer_minutes > 0:
                buffer_before_start = slot_start - timedelta(minutes=buffer_minutes)
                buffer_before_end = slot_start
                add_event_to_calendar(
                    event_store, calendar_name,
                    f"Go to {habit['habit_name']}",
                    buffer_before_start, buffer_before_end,
                    tag="[AUTO-HABIT-BUFFER]"
                )
            # Main event
            add_event_to_calendar(
                event_store, calendar_name,
                habit["habit_name"],
                slot_start, slot_end,
                tag="[AUTO-HABIT]"
            )
            # Buffer after
            if buffer_minutes > 0:
                buffer_after_start = slot_end
                buffer_after_end = slot_end + timedelta(minutes=buffer_minutes)
                add_event_to_calendar(
                    event_store, calendar_name,
                    f"Leave {habit['habit_name']}",
                    buffer_after_start, buffer_after_end,
                    tag="[AUTO-HABIT-BUFFER]"
                )
            # Remove this slot from free_slots to avoid overlap
            free_slots = [(s, e) for s, e in free_slots if e <= slot_start or s >= slot_end]
        else:
            print(f"No available slot for '{habit['habit_name']}'")

if __name__ == "__main__":
    main()