# Added on Jan 22,2024 -- To collect series of data by daily basis
import redis
from django.conf import settings

db = redis.StrictRedis('redis', 6379,db=settings.RTG_READING_VALUE_DB, 
                            charset="utf-8", decode_responses=True) #Production
from datetime import datetime

import json
def convert_to_json(data):
    result = [
        {"date": entry[0][:10], "value": entry[1]}  # Format the date and value
        for entry in data
    ]
    return result  # Return the JSON-like list of dictionaries

#Add on Jan 27,2025 -- keep number of available machine
def record_available_for_equipment_type():
    import datetime, pytz
    tz 			= pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)
    from datetime import datetime, time
    today_tz_00 = datetime.combine(today_tz, time.min)
    from maintenance.models import MachineType
    machinetypes = MachineType.objects.all()
    for mt in machinetypes:
        key = f'{mt.name}:AVAILABLE'
        collect_daily_data(today_tz_00,key,mt.machine_available)#keep number of available machine

def record_availability_for_equipment_type():
    import datetime, pytz
    tz 			= pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)
    from datetime import datetime, time
    today_tz_00 = datetime.combine(today_tz, time.min)
    from maintenance.models import MachineType
    machinetypes = MachineType.objects.all()
    for mt in machinetypes:
        key = f'{mt.name}:AVAILABILITY'
        collect_daily_data(today_tz_00,key,1 if mt.machine_available >= mt.target else 0)

def record_availability_for_equipment():
    import datetime, pytz
    tz 			= pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)
    from datetime import datetime, time
    today_tz_00 = datetime.combine(today_tz, time.min)
    from maintenance.models import Machine
    machines = Machine.objects.all()
    for mt in machines:
        key = f'{mt.name}:AVAILABILITY'
        collect_daily_data(today_tz_00,key, \
                0 if mt.on_repair > 0 else -1 if mt.on_preventive > 0 else 1)

# Added on Jan 27,2025 -- Add equpment status
def record_status_for_equipment():
    import datetime, pytz
    tz 			= pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)
    from datetime import datetime, time
    today_tz_00 = datetime.combine(today_tz, time.min)
    from maintenance.models import Machine
    machines = Machine.objects.all()
    for mt in machines:
        key = f'{mt.name}:STATUS'
        # Running   = 1
        # BD        = 0
        # CM        = -1
        # PM        = -2
        status = 1 #default is running
        if mt.failures.filter(start_date__gt=today_tz_00).count() > 0 or \
                mt.failures.filter(status='OPEN',category='BD').count() > 0 :
            status = 0 #BD
        if mt.failures.filter(start_date__gt=today_tz_00,category='CM').count() > 0 \
            or mt.failures.filter(status='OPEN',category='CM').count() > 0:
            status = -1 #CM
        if mt.pms.filter(start_date__gt=today_tz_00).count() > 0 or mt.on_preventive == 1:
            status = -2 #PM

        collect_daily_data(today_tz_00,key, status)

def collect_daily_data(current_date:datetime,key:str,value:float):
    # Get current year.
    year = current_date.year
    # Set new key
    key = f'{year}:{key}'
    db.zadd(key, {current_date.isoformat():value})

# retrive data
def get_daily_data_by_date(key:str, start_date:datetime, end_date:datetime):
    # Convert dates to ISO strings
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()
    # Get all data and filter by date range
    all_data = db.zrange(key, 0, -1, withscores=True)
    return convert_to_json([(date, int(score)) for date, score in all_data if start_iso <= date <= end_iso])

def get_daily_data_by_value(key:str, start_value:float, end_value:float):
    return convert_to_json(db.zrangebyscore(key, start_value, end_value, withscores=True))

def get_daily_data_all(key:str):
    return convert_to_json(db.zrange(key, 0, -1, withscores=True))


# Get all data
# all_data = r.zrange(key, 0, -1, withscores=True)

# Get the latest entry
# latest_data = r.zrevrange(key, 0, 0, withscores=True)