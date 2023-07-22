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


def main(req: func.HttpRequest) -> func.HttpResponse:
 
    conn_string = "dbname='postgres' user='pry20231020admin' host='pry20231020-db.postgres.database.azure.com' port='5432' password='P123456789**' sslmode='require'"

    input_name = req.get_json().get('name')
    input_username = req.get_json().get('user_name')
    input_password = req.get_json().get('password') 
    input_birth_date = req.get_json().get('birth_date')
    input_gender = req.get_json().get('gender')
    input_height= req.get_json().get('height')
    input_weight= req.get_json().get('weight')
    input_activity_level= req.get_json().get('activity_level')
   
    salt = os.urandom(16)
    N = 16384
    r = 8
    p = 1
    buflen = 32

    hashed_password = scrypt.hash(input_password.encode('utf-8'), salt, N=N, r=r, p=p, buflen=buflen)
    salt_encoded = base64.b64encode(salt).decode('utf-8')
    hashed_password_encoded = base64.b64encode(hashed_password).decode('utf-8')

    final_hash = f"$s0$e{N}${salt_encoded}${hashed_password_encoded}"

    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    query = "INSERT INTO person (name, user_name, password, birth_date, gender, height, weight, activity_level) VALUES ( %s, %s, %s, %s, %s, %s, %s, %s)"
    valores = (input_name, input_username, final_hash, input_birth_date,input_gender, input_height, input_weight, input_activity_level  )
    cursor.execute(query, valores)
    
    query = "SELECT id FROM person WHERE user_name = %s"
    valores = (input_username,)
    cursor.execute(query, valores) 
    row = cursor.fetchone()
    personid = row[0]

    # Generar una clave privada RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Obtener la clave privada en formato PEM
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    # Crear un payload con la información que deseas incluir en el token
    payload = {
        'personid': personid,
        'usuario': input_username,
        'rol': 'administrador'
    }

    # Generar el token JWT
    token = jwt.encode(payload, private_key_pem, algorithm='RS256')

    # Obtener la fecha y hora actual
    fecha_actual = datetime.now()

    query = "INSERT INTO public.session_authorization (person_id, token, date) VALUES(%s, %s, %s)"
    valores = (personid, token,fecha_actual)
    cursor.execute(query, valores)
    conn.commit()
    conn.close()

    data = {
    "id_person": personid,
    "user_name": input_username,
    "token": token
    }

    #return func.HttpResponse(json.dumps(data), mimetype="application/json")

    response_data = "{\n"
    for key, value in data.items():
        response_data += f'    "{key}": {json.dumps(value)},\n'
    response_data += "}"



    return func.HttpResponse(response_data, mimetype="application/json")

    #if input_name:
    #   return func.HttpResponse(f"Se registro con éxito. Nombre {input_name}. ")
    #else:
    #   return func.HttpResponse(
    #       "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
    #      status_code=200)
