from confluent_kafka.admin import AdminClient, NewTopic

def clear_topics(admin_client, topic_name):
    md = admin_client.list_topics(timeout=10)
    to_delete = [
        name 
        for name in md.topics.keys()
        if name != topic_name and not name.startswith("__")
    ]

    if to_delete:
        fs = admin_client.delete_topics(to_delete)
        for name, f in fs.items():
            try:
                f.result()
                print(f"deleted {name}")
            except Exception as e:
                print(f"delete {name}: {e}")
                
def create_topic(admin_client, topic_name):
    events_topic = NewTopic(topic=topic_name, num_partitions=1, replication_factor=1)
    futures = admin_client.create_topics([events_topic])
    for topic, f in futures.items():
        try:
            f.result()
            print(f"Topic {topic} created successfully")
        except Exception as e:
            print(f"Error creating topic {topic}: {e}")
        
def main():
    admin_client = AdminClient({
        "bootstrap.servers": "localhost:9092",
        "security.protocol": "PLAINTEXT",
    })
    topic_name = "spotify.events"
    
    clear_topics(admin_client, topic_name)

    create_topic(admin_client, topic_name)
            
if __name__ == "__main__":
    main() # python scripts/setup_topics.py