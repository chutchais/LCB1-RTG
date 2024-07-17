from ipaddress import ip_address
import snap7
from snap7 import util
import logging
import redis
from django.conf import settings

from machine.models import Item

db = redis.StrictRedis('redis', 6379,db=settings.RTG_READING_VALUE_DB, 
                            charset="utf-8", decode_responses=True) #Production

# Added on Oct 21,2022 -- To keep current value for all items.
def schedule_logged_value(equipment_name:str,log_for_yesterday:bool=False):
    from machine.models import Equipment
    try :
        eq      = Equipment.objects.get(name=equipment_name)
        eq.save_logged(log_for_yesterday)
        logging.info (f'Save log data of : {equipment_name} ..Successful.')
    except :
        logging.error(f'Unable to save log data of : {equipment_name}')

def schedule_read_value(equipment_name:str):
    from machine.models import Equipment
    try :
        eq      = Equipment.objects.get(name=equipment_name)
        eq.read_item_data()
        logging.info (f'Read data of : {equipment_name} ..Successful.')
    except :
        logging.error(f'Unable to read data of : {equipment_name}')

# Added on March 19,2024 -- To support reading monitor parameter for all  equipment.
def schedule_read_monitor():
    from machine.models import Equipment
    try :
        eqs      = Equipment.objects.all()
        for eq in eqs:
            eq.read_monitor_data()
        logging.info (f'Read monitor data of : {eq} ..Successful.')
    except :
        logging.error(f'Unable to read monitor data of : {eq}')


def read_value(ip:str,db_name:int,offset:int,field_type:str):
    try :
        client = snap7.client.Client()
        # client.connect(ip,0,1) # S7-1200 และ S7-1500  จะใช้เป็น Rack 0, Slot 1
        client.connect(ip,0,2) # S7-300 จะใช้เป็น Rack 0, Slot 2
        client.get_connected()

        byte_num  = 2 if field_type == 'int' else 4

        db = client.db_read(db_name, 
                            offset, 
                            byte_num) #db_read(DB number, Start address, No. of byte) 
        # t = util.get_real(db, 0)
        # t = util.get_word(db, 0)

        if byte_num == 2 :
            t = util.get_int(db, 0)#2 byte
        else :
            t = util.get_dint(db, 0) #4 byte

        # Save to by item
        # key = f'{equipment_name}:{item_name}:PREVIOUS'
        # logging.info(f'Save reading data to PREVIOUS key : {key} -->{t}')
        # save_previous_redis(key,str(t))
        return t
    except :
        logging.error(f'Unable to connect IP : {ip}')
        return -1

# Added on March 19,2024 -- To support Read 1 byte data ,specific number of bit
def read_bit(ip:str,db_name:int,offset:int,bit_number:int):
    # bit_number = base10 index number
    try :
        t=0
        client = snap7.client.Client()
        # client.connect(ip,0,1) # S7-1200 และ S7-1500  จะใช้เป็น Rack 0, Slot 1
        client.connect(ip,0,2) # S7-300 จะใช้เป็น Rack 0, Slot 2
        # Modify on JUly 17,2024 -- To check network connection
        conn = client.get_connected()
        if not conn:
            logging.error(f'Unable to connect IP : {ip}')
            return -1

        db = client.db_read(db_name, 
                            offset, 
                            1) #db_read(DB number, Start address, No. of byte) 
        t=format(db[0],'b')[::-1] #Reverst 1000 --> 0001
        # Modify on July 17,2024 -- TO fix out of range of index
        if len(t)==bit_number:
            bit_number = bit_number-1
        return int(t[bit_number])
        # return int(t[bit_number-1])
    except :
        logging.error(f'Error to read bit: {ip} : read data {t} , bit_number={bit_number}')
        return -1

def save_redis(key:str,value:dict):
    # ttl = -1
    import json
    db.hmset(key,value)
    db.publish('RTG-NOTIFY',json.dumps(value))
    # db.expire(key, ttl)

def save_previous_redis(key:str,value:str):
    db.set(key,value)

def get_previous_redis(key:str):
    value = db.get(key)
    return value if value else -1


def save_logged_item(item:Item,log_for_yesterday:bool=False):
    # Get Current value (from Redis :LATEST)
    key = f'{item.equipment.name}:{item.parameter.name}:PREVIOUS'
    current_value = get_previous_redis(key)

    # Get Current value (from Redis :YESTERDAY)
    key = f'{item.equipment.name}:{item.parameter.name}:YESTERDAY'
    last_value = get_previous_redis(key)
    last_value = last_value if last_value != -1 else current_value

    # Save current value to Yesterday.
    db.set(key,current_value)

    # Save to DataLogger
    from machine.models import DataLogger
    d = DataLogger(item=item,
                    last_value=last_value,
                    current_value=current_value)
    d.save()

    # Added on May 30,2024 - To change logged date to yesterday (same hour)
    if log_for_yesterday :
        import datetime, pytz
        from datetime import timedelta
        tz              = pytz.timezone('Asia/Bangkok')
        now_tz          = datetime.datetime.now(tz=tz)
        yesterday       = now_tz - timedelta(hours=24)

        d.created       = yesterday
        d.created_day   = yesterday.day
        d.save()


# Addded July 16,2024 -- To save to stack
def save_redis_stack(key:str,value,max_range=12):
    if db.llen (key) == max_range:
        db.lpop(key)
    db.rpush(key,value)
    return db.lrange(key,0,-1)