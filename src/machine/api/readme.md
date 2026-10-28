from machine.tasks import get_redis_data, save_redis, diagnose_redis_key
import json

# Test 1: Diagnose the problematic key
print("✓ Test 1: Diagnose Redis key")
diagnosis = diagnose_redis_key('RTG25:LATEST')
print(json.dumps(diagnosis, indent=2, default=str))

# Test 2: Migrate if needed
print("\n✓ Test 2: If it's a hash, migrate to JSON")
from redis import Redis
import os

r = Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=int(os.environ.get('REDIS_READING_DB', 0)),
    decode_responses=True
)

key = 'RTG25:LATEST'
if r.type(key) == 'hash':
    print(f"  Converting {key} from Hash to JSON...")
    data = r.hgetall(key)
    r.delete(key)
    json_str = json.dumps(data, default=str)
    r.set(key, json_str)
    print("  ✓ Converted!")

# Test 3: Get data safely
print("\n✓ Test 3: Get data safely")
data = get_redis_data('RTG25:LATEST')
print(json.dumps(data, indent=2, default=str))

# Test 4: Re-diagnose
print("\n✓ Test 4: Re-diagnose after fix")
diagnosis = diagnose_redis_key('RTG25:LATEST')
print(json.dumps(diagnosis, indent=2, default=str))