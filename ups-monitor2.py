import os
import time
import subprocess
from newrelic_telemetry_sdk import GaugeMetric, CountMetric, SummaryMetric, MetricClient, LogClient


# Don't forget to set the NEW_RELIC_LICENSE_KEY environment variable
# before running this script
def get_ups_status():
    try:
        # Run the upsc command to get UPS status
        result = subprocess.run(['upsc', 'myups'], capture_output=True, text=True, check=True)
        if result.returncode != 0:
            print('Error getting UPS status:', result.stderr)
            return None

        # Parse the output
        status = {}
        for line in result.stdout.splitlines():
            key, value = line.split(':', 1)
            status[key.strip()] = value.strip()

        return status
    except Exception as e:
        print('Exception while getting UPS status:', str(e))
        return None

def create_metric(status, name, units):
    """create a metric from the UPS status dictionary"""
    if status:
        value = float(status.get(name, 0.0))
        metric = GaugeMetric(name, value, {"units": units})
        return metric
    else:
        return None


def send_metrics():
    """send UPS metrics to New Relic"""
    status = get_ups_status()
    # pretty print status with formatting
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
            print ("Sending metric: ", metric)
            # batch.append(metric)

        response = metric_client.send_batch(batch)
        response.raise_for_status()
        print("Sent metrics successfully!")
    else:
        print('Battery not found')
        # TODO write event to new relic

while True:
    send_metrics()
    time.sleep(300)