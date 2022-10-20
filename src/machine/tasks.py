from ipaddress import ip_address
import snap7
from snap7 import util
import logging
import redis
from django.conf import settings

db = redis.StrictRedis('redis', 6379,db=settings.RTG_READING_VALUE_DB, 
                            charset="utf-8", decode_responses=True) #Production


def schedule_read_value(equipment_name:str):
    from machine.models import Equipment
    try :
        eq      = Equipment.objects.get(name=equipment_name)
        eq.read_item_data()
        logging.info (f'Read data of : {equipment_name} ..Successful.')
    except :
        logging.error(f'Unable to read data of : {equipment_name}')

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