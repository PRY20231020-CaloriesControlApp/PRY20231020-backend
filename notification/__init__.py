import psycopg2
import azure.functions as func
import scrypt
import base64
import os
import jwt
from jwt import encode
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime
import json
import numpy as np


def main(req: func.HttpRequest) -> func.HttpResponse:
 
    conn_string = "dbname='postgres' user='pry20231020admin' host='pry20231020-db.postgres.database.azure.com' port='5432' password='P123456789**' sslmode='require'"

    ##input_person_id = req.get_json().get('person_id')
 
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    query = "select id, start_date, end_date, start_time, end_time, title, message, is_active, created_at, category from notifications  where is_active = %s order by start_time asc "
    valores = (True,)

    cursor.execute(query, valores) 
    rows = cursor.fetchall()

    notifications = {}

    count  = 0
    for row in rows:
        # Obtener la información de la fila
        notifications_id = row[0]
        start_date = row[1]
        end_date = row[2]
        start_time = row[3]
        end_time = row[4]
        title = row[5]
        message = row[6]
        is_active = row[7]
        created_at = row[8]
        category = row[9]

       

        info_notifications= {
            'notifications_id':notifications_id,
            'start_date':start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'start_time': start_time.strftime('%H:%M:%S'),
            'end_time': end_time.strftime('%H:%M:%S'),
            'title':title,
            'message':message,
            'is_active': is_active,
            'created_at': created_at.isoformat(),
            'category': category
        }
        notifications[notifications_id] = info_notifications


    conn.commit()
    conn.close()




    data = {
        "notifications": list(notifications.values()) 
    }

    response_data = "{\n"
    response_items = []
    for key, value in data.items():
        if isinstance(value, np.int64):
            value = int(value)  # Convertir np.int64 a int
        response_items.append(f'    "{key}": {json.dumps(value)}')
    response_data += ",\n".join(response_items)
    response_data += "\n}"

    return func.HttpResponse(response_data, mimetype="application/json")

