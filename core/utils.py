# utils.py or somewhere reusable
from datetime import time, timedelta, datetime

def generate_daily_slots():
    start = datetime.strptime("09:00", "%H:%M")
    slots = []
    for i in range(16): 
        slot_time = (start + timedelta(minutes=30 * i)).time()
        slots.append(slot_time)
    return slots

DAILY_SLOTS = generate_daily_slots()
