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

    input_person_id = req.get_json().get('person_id')
    input_consumed_date = req.get_json().get('consumed_date')
    input_consumed_calories=req.get_json().get('consumed_calories')
    input_weight=req.get_json().get('weight')


    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    query = "INSERT INTO person_history (person_id, consumed_date, consumed_calories, weight) VALUES (%s, %s, %s, %s)"
    valores = (input_person_id, input_consumed_date, input_consumed_calories,input_weight )

    cursor.execute(query, valores)



    if cursor.rowcount == 1:
        print("Inserción exitosa: se insertó una fila.")
    else:
        print("Inserción fallida: no se insertó ninguna fila.")
    

    query = "SELECT  id, name, user_name, birth_date,gender, height, weight, activity_factor,caloric_reduction,registration_date FROM person WHERE id = %s"
    valores = (input_person_id,)
    cursor.execute(query, valores) 
    row = cursor.fetchone()
    personid = row[0]
    name = row[1]
    user_name = row[2]
    birth_date = row[3]
    gender = row[4]
    height = row[5]
    weight = row[6]
    activity_factor = row[7]
    caloric_reduction= row[8]
    registration_date= row[9]


    ##query = "SELECT id, person_id, consumed_date, consumed_calories, weight FROM public.person_history where person_id = %s"
    query = " SELECT DISTINCT ON (consumed_date) id, person_id, consumed_date, consumed_calories, weight FROM public.person_history WHERE person_id = %s ORDER BY consumed_date DESC, id DESC "
    valores = (input_person_id,)
    cursor.execute(query, valores) 
    rows = cursor.fetchall()

    progress = {}

    count  = 0
    for row in rows:
        # Obtener la información de la fila
        progress_id = row[0]
        person_id = row[1]
        consumed_date = row[2]
        consumed_calories = row[3]
        weight = row[4]

       

        info_progress= {
            'progress_id':progress_id,
            'person_id':person_id,
            'consumed_date': consumed_date.isoformat(),
            'consumed_calories': consumed_calories,
            'weight': float(weight)
        }
        progress[progress_id] = info_progress


    conn.commit()
    conn.close()

    birth_date_str = birth_date.isoformat()
    registration_date_str = registration_date.isoformat()

    age = calculate_age(birth_date)


    data = {
        "id_person": personid,
        "user_name": user_name,
        "name":name,
        "user_name":user_name,
        "birth_date":birth_date_str,
        "age": age,
        "gender": gender,
        "height": float(height),
        "weight":float(weight),
        "activity_factor": float(activity_factor),
        "caloric_reduction":caloric_reduction,
        "registration_date":registration_date_str,
        "consumed_date":input_consumed_date,
        "consumed_calories":input_consumed_calories,
        "progress": list(progress.values()) 
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

def calculate_age (birth_date):  
    fecha_actual = datetime.now()
    age = fecha_actual.year - birth_date.year
    if fecha_actual.month < birth_date.month:
        age -= 1
    elif fecha_actual.month == birth_date.month and fecha_actual.day < birth_date.day:
        age -= 1
    return age