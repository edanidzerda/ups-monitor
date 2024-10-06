"""This script monitors the status of a UPS connected to a NUT 
server and optionally sends the status to New Relic as custom metrics."""

import os
import time
from PyNUTClient import PyNUT
from newrelic_telemetry_sdk import GaugeMetric, MetricClient, LogClient

# Don't forget to set the NEW_RELIC_LICENSE_KEY environment variable
# before running this script

battery_metrics = ['battery.charge', 
                   'ups.load', 
                   'battery.voltage', 
                   'input.voltage', 
                   'battery.runtime']

def get_ups_status(host='localhost', login='', password=''):
    """get the status of the UPS from the NUT server"""
    print(f"Getting UPS information from {host}")
    print(f"Login: {login}")
    if password:
        print(f"Password: <hidden>")

    if not login:
        ups = PyNUT.PyNUTClient(host)
    else:
        ups = PyNUT.PyNUTClient(host=host, login=login, password=password)

    try:
        for name in ups.GetUPSNames():
            print ("Found UPS: ", name)
            print (ups.CheckUPSAvailable(ups=name))
            available = ups.CheckUPSAvailable(ups=name)
            if available:
                result = ups.GetUPSVars(ups=name)
                # convert binary values in response dict to plain strings
                ups_vars = {key.decode('utf-8'): value.decode('utf-8') for key, value in result.items()}
                return ups_vars
    except Exception as e:
        print(f"Failed to connect to NUT server: {e}")
        return None

    return None


def create_metric(ups_status, name, units):
    """create a metric from the UPS status dictionary"""
    if ups_status:
        value = float(ups_status.get(name, 0.0))
        metric = GaugeMetric(name, value, {"units": units})
        return metric
    else:
        return None

def get_metrics(status):
    """get UPS metrics matching desired metric strings"""
    metrics = []
    for metric in battery_metrics:
        if status.get(metric):
            metrics.append(create_metric(status, metric, "%"))
    metrics.append(GaugeMetric("ups.status", 1 if status.get('ups.status') == "OL" else 0, {"units": "boolean"}))

    return metrics


def send_metrics(status):
    """send UPS metrics to New Relic"""
    # pretty print status with formatting
    if status:
        batch = get_metrics(status)
    
        for metric in batch:
            print("Sending metric: ", metric)
            # batch.append(metric)

        if not os.environ.get("NEW_RELIC_LICENSE_KEY"):
            print("NEW_RELIC_LICENSE_KEY environment variable not set!")
            return
        
        metric_client = MetricClient(os.environ["NEW_RELIC_LICENSE_KEY"])
        try:
            response = metric_client.send_batch(batch)
            response.raise_for_status()
            print("Sent metrics successfully!")
        except Exception as e:
            print(f"Failed to send metrics: {e}")

    else:
        print('Battery not found')
        LogClient(os.environ["NEW_RELIC_LICENSE_KEY"]).send("error", "Battery not found")


# ups = os.environ.get("UPS_NAME", "myups")
ups_host = os.environ.get("UPS_HOST", "localhost")
ups_login = os.environ.get("UPS_LOGIN", "")
ups_password = os.environ.get("UPS_PASSWORD", "")
if os.environ.get("UPS_BATTERY_METRICS"):
    battery_metrics = os.environ["UPS_BATTERY_METRICS"].split(",")

if __name__ == '__main__':
    print ("Starting UPS monitor")
    while True:
        status = get_ups_status(host=ups_host, login=ups_login, password=ups_password)
        if status:
            print(status)
            send_metrics(status)
        else: 
            print('Battery not found')
        time.sleep(300)
