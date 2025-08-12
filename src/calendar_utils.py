import csv
from datetime import datetime, time, timedelta

def read_habits_from_csv(csv_path):
    habits = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            habit = {
                "habit_name": row["habit_name"],
                "duration_minutes": int(row["duration_minutes"]),
                "earliest_start": datetime.strptime(row["earliest_start"], "%H:%M").time(),
                "latest_end": datetime.strptime(row["latest_end"], "%H:%M").time(),
                "buffer_minutes": int(row["buffer_minutes"]),
                "priority": int(row["priority"]),
                "days_of_week": [int(day) for day in row["days_of_week"].split(',') if day.strip().isdigit()],
            }
            habits.append(habit)
    return habits

def find_slot_for_habit(free_slots, habit, today):
    for start, end in free_slots:
        # Restrict to habit's allowed window
        slot_start = max(start, datetime.combine(today, habit["earliest_start"]))
        slot_end = min(end, datetime.combine(today, habit["latest_end"]))
        duration = (slot_end - slot_start).total_seconds() / 60
        if duration >= habit["duration_minutes"]:
            return slot_start, slot_start + timedelta(minutes=habit["duration_minutes"])
    return None, None

# Example usage:
# habits = read_habits_from_csv("../habits.csv")
# print(habits)

def add_event(calendar_name, event_details):
    # Function to add an event to a specific calendar
    pass

def update_event(calendar_name, event_id, updated_details):
    # Function to update an existing event in a specific calendar
    pass

def delete_event(calendar_name, event_id):
    # Function to delete an event from a specific calendar
    pass

def list_events(calendar_name):
    # Function to list all events in a specific calendar
    pass