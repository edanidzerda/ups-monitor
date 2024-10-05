"""This script monitors the status of a UPS connected to a NUT 
server and sends the status to New Relic as custom metrics."""

import os
import time
from PyNUTClient import PyNUT
from newrelic_telemetry_sdk import GaugeMetric, MetricClient, LogClient

# Don't forget to set the NEW_RELIC_LICENSE_KEY environment variable
# before running this script


def get_ups_status(ups_name='myups', host='localhost', login='', password=''):
    """get the status of the UPS from the NUT server"""
    print(f"Getting UPS status for {ups_name} at {host}")
    print(f"Login: {login}")
    print(f"Password: {password}")
    if not ups_name:
        return None
    if not login:
        ups = PyNUT.PyNUTClient(host)
    else:
        ups = PyNUT.PyNUTClient(host=host, login=login, password=password)

    try:
        print (ups.CheckUPSAvailable(ups=ups_name))
        available = ups.CheckUPSAvailable(ups=ups_name)
        if available:
            result = ups.GetUPSVars(ups=ups_name)
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


def send_metrics(status):
    """send UPS metrics to New Relic"""
    # pretty print status with formatting
    if not os.environ.get("NEW_RELIC_LICENSE_KEY"):
        print("NEW_RELIC_LICENSE_KEY environment variable not set!")
        return

    if status:
        batch = [
            create_metric(status, "battery.charge", "%"),
            create_metric(status, "ups.load", "%"),
            create_metric(status, "battery.voltage", "V"),
            create_metric(status, "input.voltage", "V"),
            create_metric(status, "battery.runtime", "seconds"),
        ]
        batch.append(GaugeMetric("ups.status", 1 if status.get('ups.status') == "OL" else 0, {"units": "boolean"}))

        metric_client = MetricClient(os.environ["NEW_RELIC_LICENSE_KEY"])

        for metric in batch:
            print("Sending metric: ", metric)
            # batch.append(metric)

        response = metric_client.send_batch(batch)
        response.raise_for_status()
        print("Sent metrics successfully!")
    else:
        print('Battery not found')
        LogClient(os.environ["NEW_RELIC_LICENSE_KEY"]).send("error", "Battery not found")


ups = os.environ.get("UPS_NAME", "myups")
ups_host = os.environ.get("UPS_HOST", "localhost")
ups_login = os.environ.get("UPS_LOGIN", "")
ups_password = os.environ.get("UPS_PASSWORD", "")

while True:
    status = get_ups_status(ups_name=ups, host=ups_host, login=ups_login, password=ups_password)
    if status:
        print(status)
        send_metrics(status)
    else: 
        print('Battery not found')
    time.sleep(300)
