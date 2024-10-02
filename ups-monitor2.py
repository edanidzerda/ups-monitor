import os
import time
from newrelic_telemetry_sdk import GaugeMetric, CountMetric, SummaryMetric, MetricClient, LogClient
import subprocess

# Don't forget to set the NEW_RELIC_LICENSE_KEY environment variable

def get_ups_status():
    try:
        # Run the upsc command to get UPS status
        result = subprocess.run(['upsc', 'myups'], capture_output=True, text=True)
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


def send_metrics():
    status = get_ups_status()
    # pretty print status with formatting
    if status:
        
        health = float(status.get('battery.charge', 0.0))
        load = float(status.get('ups.load', 0.0))
        battery_voltage = float(status.get('battery.voltage', 0.0))
        input_voltage = float(status.get('input.voltage', 0.0))
        battery_runtime = float(status.get('battery.runtime', 0.0))
        power_status = status.get('ups.status')

        status = get_ups_status()
        if status:
            health = float(status.get('battery.charge', 0.0))
            load = float(status.get('ups.load', 0.0))
            battery_voltage = float(status.get('battery.voltage', 0.0))
            input_voltage = float(status.get('input.voltage', 0.0))
            battery_runtime = float(status.get('battery.runtime', 0.0))
            power_status = status.get('ups.status')

            metrics = {
                "battery.charge": {"value": health, "units": "%"},
                "ups.load": {"value": load, "units": "%"},
                "battery.voltage": {"value": battery_voltage, "units": "V"},
                "input.voltage": {"value": input_voltage, "units": "V"},
                "battery.runtime": {"value": battery_runtime, "units": "seconds"},
                "ups.status": {"value": power_status, "units": ""}
            }

            metric_client = MetricClient(os.environ["NEW_RELIC_LICENSE_KEY"])
            batch = []

            for name, data in metrics.items():
                print ("Sending metric: ", name)
                metric = GaugeMetric(name, data["value"], {"units": data["units"]})
                batch.append(metric)

            response = metric_client.send_batch(batch)
            response.raise_for_status()
            print("Sent metrics successfully!")
            print('Health:', health)
            print('Status:', power_status)
        else:
            print('Battery not found')
    else:
        print('Battery not found')

while True:
    send_metrics()
    time.sleep(300)