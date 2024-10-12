"""This script monitors the status of a UPS connected to a NUT 
server and optionally sends the status to New Relic as custom metrics."""

import os
import time
from PyNUTClient import PyNUT
from newrelic_telemetry_sdk import GaugeMetric, MetricClient, LogClient
import threading
from flask import Flask, jsonify, render_template, request
from datetime import datetime
import json
import sqlite3

database_name = 'example.db'

# Don't forget to set the NEW_RELIC_LICENSE_KEY environment variable
# before running this script
global_status = {}
desired_metrics = {}
battery_metrics = ['battery.charge',
                   'ups.load', 
                   'battery.voltage', 
                   'input.voltage', 
                   'battery.runtime']

def get_iso8601_timestamp():
    return datetime.now().isoformat() + 'Z'

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
    ups_vars = {}
    
    try:
        for name in ups.GetUPSNames():
            print ("Found UPS: ", name)
            available = ups.CheckUPSAvailable(ups=name)
            if available:
                result = ups.GetUPSVars(ups=name)
                # convert binary values in response dict to plain strings
                ups_vars = {key.decode('utf-8'): value.decode('utf-8') for key, value in result.items()}
    except Exception as e:
        print(f"Failed to connect to NUT server: {e}")
        ups_vars["error"] = str(e)

    ups_vars["ups.host"] = host
    ups_vars["ups.login"] = login
    ups_vars["timestamp"] = get_iso8601_timestamp()

    return ups_vars


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
            desired_metrics[metric] = status.get(metric)
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

# Run this block in a background thread

def background_ups_monitor():
    """This function will run in a background thread to monitor the UPS status"""
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    while True:
        print("Checking UPS stats on thread: ",threading.current_thread())
        status = get_ups_status(ups_host, ups_login, ups_password)
        if status:
            write_to_db(status)
            global_status.update(status)
            send_metrics(status)
        time.sleep(300)


def write_to_db(stats):
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute(''' INSERT INTO metrics (data) VALUES (?)''',(json.dumps(stats),))
    print("Writing to DB: ", desired_metrics)
    conn.commit()
    conn.close()


# ups = os.environ.get("UPS_NAME", "myups")
ups_host = os.environ.get("UPS_HOST", "localhost")
ups_login = os.environ.get("UPS_LOGIN", "")
ups_password = os.environ.get("UPS_PASSWORD", "")
if os.environ.get("UPS_BATTERY_METRICS"):
    battery_metrics = os.environ["UPS_BATTERY_METRICS"].split(",")

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html', global_status=desired_metrics)

@app.route('/metrics')
def metrics_route():
    """return the current UPS status as JSON"""
    return jsonify(global_status)

# @app.route('/metrics/history')
# def metrics_history():
#     key = request.args.get('key', 'battery.charge')  # Default to 'battery.charge' if no key is provided
#     conn = sqlite3.connect(database=database_name)
#     c = conn.cursor()
    
#     # Use parameterized query to prevent SQL injection
#     query = f'SELECT timestamp, json_extract(data, ?) AS value FROM metrics ORDER BY timestamp DESC'
#     c.execute(query, (f'$."{key}"',))
#     rows = c.fetchall()
#     conn.close()
    
#     history = [{'timestamp': row[0], 'value': row[1]} for row in rows]
    
#     return jsonify(history)

@app.route('/metrics/history')
def metrics_history():
    key = request.args.get('key', 'battery.charge')  # Default to 'battery.charge' if no key is provided
    dateRange = request.args.get('range', '60')
    print("Date Range: ", dateRange)
    conn = sqlite3.connect(database_name)
    c = conn.cursor()
    
    # Use parameterized query to prevent SQL injection
    query = f'''
    SELECT strftime('%H:%M', datetime(timestamp, 'localtime')) as timestamp
        , json_extract(data, ?) AS value 
      FROM metrics 
      WHERE TIMESTAMP > datetime('now', ?)
      ORDER BY timestamp ASC'''
    
    print("Executing query:", query)
    print("With parameters:", (f'$.{key}', f'-{dateRange} minutes'))

    c.execute(query, (f'$."{key}"',f'-{dateRange} minutes'))
    rows = c.fetchall()
    conn.close()
    
    # Prepare data for Chart.js
    labels = [row[0] for row in rows]
    data = [row[1] for row in rows]
    
    chart_data = {
        "labels": labels,
        "datasets": [
            {
                "label": key,
                "data": data
            }
        ]
    }
    
    return jsonify(chart_data)

@app.route('/metrics/keys')
def metrics_keys():
    conn = sqlite3.connect(database=database_name)
    c = conn.cursor()
    
    # Select all keys from the JSON data
    c.execute('''
        SELECT DISTINCT json_each.key
        FROM metrics, json_each(metrics.data)
        ORDER BY json_each.key
    ''')
    rows = c.fetchall()
    conn.close()
    
    # Convert the list of tuples to a list of keys
    keys = [row[0] for row in rows]
    
    return jsonify(keys)
if __name__ == '__main__':

    # Connect to the SQLite database

    conn = sqlite3.connect(database_name)
    c = conn.cursor()

    # Create a table with a JSON column
    c.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            data TEXT  -- Store JSON data as TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print ("Starting UPS monitor")
    # Run this block in a background thread
    background_thread = threading.Thread(name='Background Monitor', target=background_ups_monitor, daemon=True)
    background_thread.start()
    app.run(host='0.0.0.0',port=5001, debug=True)

    
