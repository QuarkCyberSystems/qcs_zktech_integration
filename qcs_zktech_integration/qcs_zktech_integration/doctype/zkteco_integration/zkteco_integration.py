# Copyright (c) 2024, Quark Cyber Systems FZC and contributors
# For license information, please see license.txt

import frappe
import json
import requests

from frappe.model.document import Document
from frappe.utils import today, add_to_date
from datetime import datetime


class ZKTecoIntegration(Document):
    pass


def daily_sync_transactions():
    enable_daily_sync = frappe.db.get_single_value('ZKTeco Integration', 'enable_daily_sync')
    if enable_daily_sync == 1:
        sync_date = add_to_date(today(), days=-1)
        get_transactions(sync_date, sync_date)


@frappe.whitelist()
def get_transactions(from_date, to_date):
    try:
        zkteco_settings = frappe.get_doc('ZKTeco Integration')
        if (zkteco_settings.api_url and zkteco_settings.username and zkteco_settings.password):
            url = zkteco_settings.api_url
            username = zkteco_settings.username
            pwd = zkteco_settings.password
            token = authentication(url, username, pwd)
            if not token:
                integration_log_entry('Failed to retrieve token')
                return

            transactions_url = url + '/iclock/api/transactions/'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'JWT {token}'
            }
            start_time = from_date + ' 00:00:00'
            end_time = to_date + ' 23:59:59'
            params = {
                'page': 1,
                'page_size': 10000,
                'start_time': start_time,
                'end_time': end_time
            }

            response = requests.get(transactions_url, headers=headers, params=params)
            transactions = response.json()
            data = transactions.get('data')

            if data:
                for record in data:
                    emp_code = record.get('emp_code')
                    employee = frappe.db.get_value('Employee', {'attendance_device_id': emp_code}, 'name')
                    if employee:
                        check_in_doc = frappe.new_doc('Employee Checkin')
                        punch_time_dt = datetime.strptime(record.get('punch_time'), '%Y-%m-%d %H:%M:%S')
                        if record.get('punch_state_display') == 'Check In':
                            check_in_doc.update({
                                'employee': employee,
                                'log_type': 'IN',
                                'time': punch_time_dt
                            })
                        else:
                            check_in_doc.update({
                                'employee': employee,
                                'log_type': 'OUT',
                                'time': punch_time_dt
                            })
                        check_in_doc.save(ignore_permissions=True)
            else:
                message = 'No data found'
                integration_log_entry(message)

    except requests.exceptions.HTTPError as http_err:
        message = f'HTTP error has occurred: {http_err}'
        integration_log_entry(message)

    except requests.exceptions.ConnectionError as conn_err:
        message = f'Connection error has occurred: {conn_err}'
        integration_log_entry(message)

    except requests.exceptions.Timeout as timeout_err:
        message = f'Timeout error has occurred: {timeout_err}'
        integration_log_entry(message)

    except requests.exceptions.RequestException as req_err:
        message = f'An error has occurred: {req_err}'
        integration_log_entry(message)

    except Exception as err:
        message = f'An unexpected error has occurred: {err}'
        integration_log_entry(message)


def authentication(api_url, username, pwd):
    url = api_url + '/jwt-api-token-auth/'
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        'username': username,
        'password': pwd
    }
    response = requests.post(url, data=json.dumps(data), headers=headers)
    res_tech = response.json()
    token = res_tech.get('token')
    if token:
        return token
    else:
        integration_log_entry('No token found in the response')
        return None


def integration_log_entry(message):
    integration_log = frappe.new_doc('ZKTeco Integration Log')
    integration_log.update({
        'transaction_date': today(),
        'response': message
    })
    integration_log.save(ignore_permissions=True)
