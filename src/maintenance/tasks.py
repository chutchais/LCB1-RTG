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


def send_engine_hour_report(to_email,send_email,server='192.168.1.15'):
    import smtplib  
    from email.message import EmailMessage

    import datetime, pytz
    tz 		    = pytz.timezone('Asia/Bangkok')
    today_tz 	=   datetime.datetime.now(tz=tz)

    # Run generate operation report
    # df_week,df_today = get_rtg_productivity_dataframe()
    
    msg = EmailMessage()  
    msg['Subject'] = f'Mobile Equipment Engine Hour Report : {today_tz.strftime("%d-%b-%Y %H:%M")}'  
    msg['From'] = send_email 
    msg['To'] = to_email

    from maintenance.models import Machine
    machines = Machine.objects.filter(machine_type__in=['TOPLIFT','RS']).order_by('name')    
    content = "<h3>Mobile Equipment Engine Hour Report</h3>"
    content += f"<p>Report Date : {today_tz.strftime('%d-%b-%Y %H:%M')}</p>"
    content += "<table border='1' cellpadding='5' cellspacing='0'>"     
    content += "<tr><th>Machine</th><th>Engine Hour</th><th>Move</th></tr>"
    for mt in machines:
        content += f"<tr><td>{mt.name}</td><td align='right'>{mt.engine_hour if mt.engine_hour else 0}</td><td align='right'>{mt.engine_move if mt.engine_move else 0}</td></tr>"
    content += "</table>"
    msg.add_alternative(content, subtype='html')

    # ส่งอีเมล  
    with smtplib.SMTP(server) as server:  
        server.send_message(msg)


def send_pm_status_report_with_monitoring(to_email=None, send_email=None, server='192.168.1.15'):
    """Daily PM status report with data staleness monitoring.

    Sends an HTML email listing all TOPLIFT/RS machines with their current
    engine_hour, engine_move, last MQTT update timestamp and a FRESH/STALE
    status indicator.  Stale machines are highlighted in red.
    """
    import smtplib
    from email.message import EmailMessage
    import datetime, pytz
    from django.conf import settings as django_settings

    tz = pytz.timezone('Asia/Bangkok')
    today_tz = datetime.datetime.now(tz=tz)

    threshold_hours = getattr(django_settings, 'PM_DATA_STALENESS_THRESHOLD_HOURS', 2)

    if to_email is None:
        to_email = getattr(django_settings, 'PM_REPORT_RECIPIENT_EMAIL', '')
    if send_email is None:
        send_email = getattr(django_settings, 'PM_REPORT_SENDER_EMAIL', '')

    from maintenance.models import Machine
    machines = Machine.objects.filter(machine_type__in=['TOPLIFT', 'RS']).order_by('name')

    stale_count = 0
    rows = []
    for m in machines:
        is_stale = m.data_is_stale(threshold_hours=threshold_hours)
        if is_stale:
            stale_count += 1
        rows.append({
            'name': m.name,
            'engine_hour': m.engine_hour if m.engine_hour is not None else 0,
            'engine_move': m.engine_move if m.engine_move is not None else 0,
            'last_update': m.last_mqtt_update(),
            'is_stale': is_stale,
        })

    msg = EmailMessage()
    msg['Subject'] = f'PM Status Report with Data Monitoring : {today_tz.strftime("%d-%b-%Y %H:%M")}'
    msg['From'] = send_email
    msg['To'] = to_email

    content = "<h3>PM Status Report with Data Monitoring</h3>"
    content += f"<p>Report Date/Time : {today_tz.strftime('%d-%b-%Y %H:%M')}</p>"
    content += f"<p>Total Machines : {len(rows)} | "
    content += f"<span style='color:red;font-weight:bold;'>Stale Data : {stale_count}</span></p>"
    content += "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse;'>"
    content += ("<tr style='background-color:#4472C4;color:white;'>"
                "<th>Machine Name</th><th>Engine Hour</th><th>Move</th>"
                "<th>Last Update</th><th>Status</th></tr>")
    for row in rows:
        if row['is_stale']:
            row_style = "background-color:#FFE0E0;"
            status_cell = "<td style='color:red;font-weight:bold;'>&#9888; STALE</td>"
        else:
            row_style = ""
            status_cell = "<td style='color:green;font-weight:bold;'>&#10003; FRESH</td>"
        content += (f"<tr style='{row_style}'>"
                    f"<td>{row['name']}</td>"
                    f"<td align='right'>{row['engine_hour']}</td>"
                    f"<td align='right'>{row['engine_move']}</td>"
                    f"<td>{row['last_update']}</td>"
                    f"{status_cell}</tr>")
    content += "</table>"
    content += (f"<p style='color:gray;font-size:0.85em;'>"
                f"Generated : {today_tz.strftime('%d-%b-%Y %H:%M')} | "
                f"Staleness threshold : {threshold_hours} hour(s)</p>")

    msg.add_alternative(content, subtype='html')

    with smtplib.SMTP(server) as smtp_server:
        smtp_server.send_message(msg)  