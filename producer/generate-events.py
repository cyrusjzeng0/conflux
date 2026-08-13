from faker import Faker
import random
import time
import json

fake = Faker()

EVENTS = ["play_song", "song_liked", "song_unliked", "create_new_playlist", "add_song_to_playlist", "remove_song_from_playlist", "delete_playlist"]
SUBSCRIPTION_TYPES = ["free", "premium"]

USER_IDS = [fake.uuid4() for _ in range(1000)]
SONG_IDS = [fake.uuid4() for _ in range(12000)]
PLAYLIST_IDS = [fake.uuid4() for _ in range(2000)]

def build_properties(event_type: str) -> dict:
    if event_type in ["play_song", "song_liked", "song_unliked"]:
        return {
            "song_id": random.choice(SONG_IDS)
        }
    elif event_type == "create_new_playlist":
        return {
            "playlist_name": fake.word()
        }
    elif event_type in ["add_song_to_playlist", "remove_song_from_playlist"]:
        return {
            "playlist_id": random.choice(PLAYLIST_IDS),
            "song_id": random.choice(SONG_IDS)
        }
    elif event_type == "delete_playlist":
        return {
            "playlist_id": random.choice(PLAYLIST_IDS)
        }

def generate_batch_events(events_per_timeframe: int):
    events = []
    for _ in range(events_per_timeframe):
        event_type = random.choice(EVENTS)
        payload = {
            "event_id": fake.uuid4(),
            "event_type": event_type, 
            "event_timestamp": fake.date_time_this_year().isoformat(),
            "user_id": random.choice(USER_IDS),
            "user_country": fake.country(),
            "user_subscription_type": random.choice(SUBSCRIPTION_TYPES),
            "event_properties": build_properties(event_type)
        }
        events.append(payload)
    
    return events
    
sleep_time = 0.5

def main():
    while True:
        num_events = random.randint(0, 5)
        print(json.dumps(generate_batch_events(num_events)))
        time.sleep(sleep_time)

if __name__ == "__main__":
    main() # run with python3 -m producer.generate-events