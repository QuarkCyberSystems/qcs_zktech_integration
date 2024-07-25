import json
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from datetime import datetime
import frappe


def bio_auth(url, user_name, pwd):
    url = url + "/jwt-api-token-auth/"
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "username": user_name,
        "password": pwd
    }

    response = requests.post(url, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    res_tech = response.json()
    token = res_tech.get("token")
    if token:
        return token
    else:
        frappe.errprint("No token found in the response")
        return None


def get_transactions():
    try:
        zktech_settings = frappe.get_doc("ZKTeck API Settings")
        if (zktech_settings.url and zktech_settings.user_name and zktech_settings.password):
            frappe.errprint("Getting transactions...")
            url = zktech_settings.url
            user_name = zktech_settings.user_name
            pwd = zktech_settings.password
            
            token = bio_auth(url, user_name, pwd)
            if not token:
                frappe.errprint("Failed to retrieve token")
                return

            transactions_url = url + "/iclock/api/transactions/"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"JWT {token}"
            }

            start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
            end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999).strftime('%Y-%m-%d %H:%M:%S')

            params = {
                "page": 1,
                "page_size": 100,
                "start_time": start_time,
                "end_time": end_time,
            }

            response = requests.get(transactions_url, headers=headers, params=params)
            response.raise_for_status()
            transactions = response.json()
            data = transactions.get("data")
            if data:
                for record in data:
                    emp_code = record.get("emp_code")
                    emp_all_doc = frappe.get_all("Employee", filters={"attendance_device_id": emp_code}, fields=["name", "attendance_device_id"])
                    if emp_all_doc:
                        for emp in emp_all_doc:
                            emp_doc = frappe.get_doc("Employee", emp.get("name"))
                            check_in_doc = frappe.new_doc("Employee Checkin")
                            punch_time_dt = datetime.strptime(record.get("punch_time"), '%Y-%m-%d %H:%M:%S')
                            
                            if record.get("punch_state_display") == "Check In":
                                check_in_doc.update({
                                    "employee": emp_doc.name,
                                    "employee_name": emp_doc.employee_name,
                                    "log_type": "IN",
                                    "time": punch_time_dt
                                })
                            else:
                                check_in_doc.update({
                                    "employee": emp_doc.name,
                                    "employee_name": emp_doc.employee_name,
                                    "log_type": "OUT",
                                    "time": punch_time_dt
                                })
                            check_in_doc.save(ignore_permissions=True)
            else:
                error_log = frappe.new_doc("ZKTeck API Error Log")
                error_log.update({
                    "error_message": "No data found"
                })
                error_log.save(ignore_permissions=True)

    except requests.exceptions.HTTPError as http_err:
        error_log = frappe.new_doc("ZKTeck API Error Log")
        error_log.update({
            "error_message": f"HTTP error occurred: {http_err}"
        })
        error_log.save(ignore_permissions=True)
    except requests.exceptions.ConnectionError as conn_err:
        error_log = frappe.new_doc("ZKTeck API Error Log")
        error_log.update({
            "error_message": f"Connection error occurred: {conn_err}"
        })
        error_log.save(ignore_permissions=True)
    except requests.exceptions.Timeout as timeout_err:
        error_log = frappe.new_doc("ZKTeck API Error Log")
        error_log.update({
            "error_message": f"Timeout error occurred: {timeout_err}"
        })
        error_log.save(ignore_permissions=True)
    except requests.exceptions.RequestException as req_err:
        error_log = frappe.new_doc("ZKTeck API Error Log")
        error_log.update({
            "error_message": f"An error occurred: {req_err}"
        })
        error_log.save(ignore_permissions=True)
    except Exception as err:
        error_log = frappe.new_doc("ZKTeck API Error Log")
        error_log.update({
            "error_message": f"An unexpected error occurred: {err}"
        })
        error_log.save(ignore_permissions=True)
