import unittest
import os
from unittest.mock import patch, MagicMock
from ups_monitor import send_metrics, create_metric

class TestUPSMonitor(unittest.TestCase):

    @patch('ups_monitor.PyNUT.PyNUTClient')
    @patch('ups_monitor.MetricClient')
    @patch('ups_monitor.LogClient')
    def test_send_metrics(self, MockPyNutClient, MockMetricClient, MockLogClient):
        # Create a mock instance of MetricClient
        mock_metric_client = MockMetricClient.return_value
        mock_log_client = MockLogClient.return_value
        os.environ["NEW_RELIC_LICENSE_KEY"] = "1234"
        # Mock the send_batch method
        mock_metric_client.send_batch.return_value = MagicMock()

        # Mock the status dictionary
        status = {
            'battery.charge': '100',
            'ups.load': '50',
            'battery.voltage': '12.0',
            'input.voltage': '120.0',
            'battery.runtime': '300',
            'ups.status': 'OL'
        }

        # Call the function to test
        send_metrics(status)

        # Verify that send_batch was called once
        mock_metric_client.send_batch.assert_called_once()

    @patch('ups_monitor.PyNUT.PyNUTClient')
    def test_create_metric(self, MockPyNUTClient):
        # Mock status dictionary
        status = {
            'battery.charge': '100',
            'ups.load': '50'
        }

        # Call the function to test
        metric = create_metric(status, 'battery.charge', '%')
        
        # Verify the result
        self.assertEqual(metric.name, 'battery.charge')
        self.assertEqual(metric.value, 100.0)

if __name__ == '__main__':
    unittest.main()