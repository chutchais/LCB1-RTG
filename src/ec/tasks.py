import logging
import redis
from django.conf import settings

import pyodbc


from fastapi.logger import logger
import logging
gunicorn_logger = logging.getLogger('gunicorn.error')
logger.handlers = gunicorn_logger.handlers

db = redis.StrictRedis('redis', 6379,db=settings.RTG_READING_VALUE_DB, 
                            charset="utf-8", decode_responses=True) #Production


#setup db connection to sql server
def init_db():
	# Modify on Dec 19,2022 -- To support env
	import os
	driver		= '{ODBC Driver 17 for SQL Server}'#'FreeTDS'#
	server		= os.environ['N4_HOST']
	database	= os.environ['N4_DATABASE']
	username	= os.environ['N4_USERNAME']
	password	= os.environ['N4_PASSWORD']
	cnxn = pyodbc.connect('DRIVER='+driver+';SERVER='+server+
                        ';PORT=1433;DATABASE='+database+
                        ';UID='+username+';PWD='+ password)
	cursor = cnxn.cursor()

	return cursor

def db_n4_get_events():
	cursor_n4  = init_db()
	
	# Added on June 9,2023 -- To support Shore for LKB (Import Delivery Order) with prefix 'S-'
	cursor_n4.execute("SELECT	u.id container, g.bl_nbr booking " \
					"FROM inv_unit AS u WITH (nolock)  inner join " \
					"ref_equipment AS eq WITH (nolock) ON u.eq_gkey = eq.gkey inner join " \
					"ref_equip_type AS eqt WITH (nolock) ON eq.eqtyp_gkey = eqt.gkey left outer join " \
					"ref_bizunit_scoped AS agent WITH (nolock) ON u.agent1 = agent.gkey left outer join " \
					"ref_bizunit_scoped AS line WITH (nolock) ON u.line_op = line.gkey left outer join " \
					"inv_goods AS g WITH (nolock) ON u.goods = g.gkey " \
					"where g.bl_nbr=''")

	
	rows = cursor_n4.fetchall()
    # return None
##############################################################