import psycopg2
import azure.functions as func
from jwt import encode
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime
import json
import numpy as np



def main(req: func.HttpRequest) -> func.HttpResponse:

    fecha_actual = datetime.now()
 
    conn_string = "dbname='postgres' user='pry20231020admin' host='pry20231020-db.postgres.database.azure.com' port='5432' password='P123456789**' sslmode='require'"

    input_person_id = req.get_json().get('person_id')
    input_meal_id = req.get_json().get('meal_id')
    input_liked = req.get_json().get('liked')
    ##input_feedback_date = req.get_json().get('feedback_date')
   
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    query = "INSERT INTO public.recommendation_feedback (person_id, meal_id, liked, feedback_date) VALUES (%s, %s, %s, %s)"
   
    valores = (input_person_id, input_meal_id, input_liked,fecha_actual )

    cursor.execute(query, valores)


    if cursor.rowcount == 1:
        print("Inserción exitosa: se insertó una fila.")
    else:
        print("Inserción fallida: no se insertó ninguna fila.")
    
    conn.commit()
    conn.close()


    data = {
        "id_person": input_person_id,
        "meal_id":input_meal_id,
        "liked":input_liked,
        "feedback_date":fecha_actual.isoformat()
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

