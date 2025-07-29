# yourapp/management/commands/mqtt_subscriber.py
from django.core.management.base import BaseCommand
import paho.mqtt.client as mqtt
# from ma.models import YourModel  # Import your model
import redis
from django.conf import settings

db = redis.StrictRedis('redis', 6379,db= 2, 
                            charset="utf-8", decode_responses=True) #Production
from datetime import datetime

class Command(BaseCommand):
    help = 'Subscribes to MQTT topics and saves data to database'

    def handle(self, *args, **options):
        client = mqtt.Client()
        
        def on_connect(client, userdata, flags, rc):
            print("Connected with result code "+str(rc))
            client.subscribe("engine/#")  # Subscribe to your topic
        
        def on_message(client, userdata, msg):
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 3:
                client_id = topic_parts[1]
                print(f"📍 From client ID: {client_id}")
                print(f"📦 Message: {msg.payload.decode()}")
                save_mqtt_message(client_id,topic_parts[2],msg.payload.decode())
                # Added on Sep 28,2025 -- To save to redis structure format
                _, engine_name, data_type = topic_parts
                value = msg.payload.decode()
                # Data type conversion
                if data_type == "hour":
                    value = float(value)
                elif data_type == "move":
                    value = int(value)
                # Save to Redis as a hash
                import datetime, pytz
                tz 			= pytz.timezone('Asia/Bangkok')
                today_tz 	=   datetime.datetime.now(tz=tz)

                redis_key = f"engine:{engine_name}"
                db.hset(redis_key, mapping={
                    data_type: value,
                    "last_update": today_tz.now().isoformat()
                })
                print(f"📥 Saved {engine_name} {data_type} = {value}")


        client = mqtt.Client(client_id="mosquitto-client")

        # Set credentials if broker requires authentication
        client.username_pw_set("telematic", "lcb12025")

        # Set event callbacks
        client.on_connect = on_connect
        # client.on_disconnect = on_disconnect
        # client.on_log = on_log
        client.on_message = on_message

        print("🔌 Connecting to broker...")
        client.connect("mosquitto", 1883, 120)

        # Start the loop to process callbacks
        client.loop_forever()

def save_mqtt_message(client_id, data_type, payload):
    key = f"{client_id}:{data_type}"
    db.set(key, payload)
    # To save time stamp
    import datetime, pytz
    tz 			= pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)
    key = f"{client_id}:updated"
    db.set(key, today_tz.strftime('%d-%b-%Y %H:%M'))

def get_mqtt_message(client_id, data_type):
    key = f"{client_id}:{data_type}"
    return db.get(key)