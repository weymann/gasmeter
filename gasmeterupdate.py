#!/usr/bin/python3

import py_qmc5883l
import time
import requests
import json
import asyncio
import background
import logging
from datetime import datetime
from requests.auth import HTTPBasicAuth
from systemd.journal import JournaldLogHandler

@background.task
def post():
	# report values every minute
	#print("Post data Total")
	response = requests.post("http://smarthome:8080/rest/items/GasMeterTotal",str(gas_meter_total),headers={'Content-Type': 'text/plain'})
	#print("Post data Daily")
	response = requests.post("http://smarthome:8080/rest/items/GasMeterDaily",str(gas_meter_daily),headers={'Content-Type': 'text/plain'})
	#print("Post data Minute")
	response = requests.post("http://smarthome:8080/rest/items/GasMeterMinute",str(gas_meter_minute),headers={'Content-Type': 'text/plain'})
	#print("Sucess Rate: "+str(success_rate))
	response = requests.post("http://smarthome:8080/rest/items/GasMeterReadSuccess",str(success_rate),headers={'Content-Type': 'text/plain'})
	#print(response)
	now = datetime.now()
	current_time = now.strftime("%d/%m/%y %H:%M:%S")
	# print(current_time + " post done")
	logger.info(current_time+":"+str(response.status_code))

normal = 5000
hysteresis = 2000
sensor_init = 0
read_interval = 2
state = "init"
loop_counter = 1
loop_time = 60
gas_meter_total = 0
gas_meter_daily = 0
gas_meter_minute = 0
last_sensor_date = datetime.today().date()
read_success = 0
read_fail = 0
success_rate = 0.0
auth = HTTPBasicAuth('user', 'oh.GasMeter.JS5AYkKcWRREm3vBjjI4KAoSgmZNDV86yffO0WBpD8RIm9jrJbu331bvtH3q8PofwJvJMmSoLSslZqUAqKOA')

# get an instance of the logger object this module will use
logger = logging.getLogger(__name__)
# instantiate the JournaldLogHandler to hook into systemd
journald_handler = JournaldLogHandler()
# set a formatter to include the level name
journald_handler.setFormatter(logging.Formatter(
    '[%(levelname)s] %(message)s'
))
# add the journald handler to the current logger
logger.addHandler(journald_handler)
# optionally set the logging level
logger.setLevel(logging.DEBUG)

while sensor_init == 0:
	total_response = requests.get("http://smarthome:8080/rest/items/GasMeterTotal")
	gas_meter_total = int(total_response.json()["state"])
	# print(str(gas_meter_total))
	logger.info("Get GasMeter total value " + str(gas_meter_total))
	daily_response = requests.get("http://smarthome:8080/rest/items/GasMeterDaily")
	gas_meter_daily = int(daily_response.json()["state"])
	# print(str(gas_meter_daily))
	logger.info("Get GasMeter daily value " + str(gas_meter_daily))
	try:
		sensor = py_qmc5883l.QMC5883L(output_range=py_qmc5883l.RNG_8G)
		sensor_init = 1
		logger.info("Sensor init done")
		# print("Sensor init done")
	except IOError:
		# print("Sensor init error")
		logger.info("Sensor init error - retry")
		time.sleep(5)


# print("Start measure")
# response = requests.post("http://smarthome:8080/rest/items/GasMeterReadSuccess",str(loop_time),headers={'Content-Type': 'text/plain'})
# print(response)
while 1==1:
	try:
		m = sensor.get_magnet_raw()
		read_success += 1
		if m[1] < normal - hysteresis:
			if state == "init":
				state = "count"
			if state == "idle":
				state = "count"
				# print("Tik")
				gas_meter_minute += 10
				gas_meter_daily = gas_meter_daily + 10
				gas_meter_total += 10
		if m[1] > normal:
			if state == "init":
				state = "idle"
			if state == "count":
				state = "idle"
				# print("Tok")
	except IOError:
		# print("IOError")
	        # count IOErrors
		read_fail += 1
	tod = datetime.today().date()
	if last_sensor_date < tod:
		# after day changes reset daily values
		total_response = requests.get("http://smarthome:8080/rest/items/GasMeterTotal")
		gas_meter_total = total_response.json()["state"]
		last_time = last_sensor_date.strftime("%d/%m/%y %H:%M")
		now_time = now.strftime("%d/%m/%y %H:%M")
		# print("Day Switch from "+last_time+" to "+now_time)
		logger.info("Day Switch from "+last_time+" to "+now_time)
		last_sensor_date = datetime.today().date()
		gas_meter_daily = 0
		# report read / success rate for each day
		read_fail = 0
		read_success = 0
	if loop_counter >= loop_time:
		# log minutely entries
		now = datetime.now()
		current_time = now.strftime("%d/%m/%y %H:%M:%S")
		if read_success == 0:
			success_rate = 0.0
		else:
			success_rate = round(100.0 - (float(read_fail) * 100 / float(read_success)),1)
		# print(current_time + ", Total: " + str(gas_meter_total)+", Daily: "+str(gas_meter_daily)+", Minute: "+str(gas_meter_minute)+" Success Rate: "+str(success_rate)+" Success: "+str(read_success)+" Fail: "+str(read_fail))
		logger.info(current_time + ", Total: " + str(gas_meter_total)+", Daily: "+str(gas_meter_daily)+", Minute: "+str(gas_meter_minute)+" Success Rate: "+str(success_rate)+" Success: "+str(read_success)+" Fail: "+str(read_fail))
		post()

		# reset loop counter and minutely consumption
		loop_counter = 1
		gas_meter_minute = 0
	# increase loop counter and sleep
	loop_counter = loop_counter + read_interval
	time.sleep(read_interval)

