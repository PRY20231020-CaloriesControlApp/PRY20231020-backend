import psycopg2
import azure.functions as func
import scrypt 

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

import jwt
from jwt import encode

from datetime import datetime
import base64
import json

def main(req: func.HttpRequest) -> func.HttpResponse:  
    conn_string = "dbname='postgres' user='pry20231020admin' host='pry20231020-db.postgres.database.azure.com' port='5432' password='P123456789**' sslmode='require'"
      
    input_username = req.get_json().get('user_name')
    input_password = req.get_json().get('password') 

    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    query = "SELECT password FROM person WHERE user_name = %s"
    valores = (input_username,)
    cursor.execute(query, valores)
    row = cursor.fetchone()

    if row and input_password is not None:
        if verify_password(input_password, row[0]):
            
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

            response_data = "{\n"
            for key, value in data.items():
                response_data += f'    "{key}": {json.dumps(value)},\n'
            response_data += "}"

            return func.HttpResponse(response_data, mimetype="application/json")
            #return func.HttpResponse(f"Inicio de sesión de éxito. Usuario: {input_username}. Token: {token} ")
                      
        else:
            conn.close()
            return func.HttpResponse("La contraseña es incorrecta.")
    else:
        conn.close()
        return func.HttpResponse("Usuario no encontrado")
    

def verify_password(input_password, final_hash):
    # Descomponer el hash final en sus componentes
    parts = final_hash.split("$")
    N = int(parts[2][1:])  # Saltarse el primer caracter 'e'
    r = 8
    p = 1
    buflen = 32
    salt_encoded = parts[3]
    hashed_password_encoded = parts[4]

    # Decodificar el salt y el hash desde base64
    salt = base64.b64decode(salt_encoded)
    hashed_password = base64.b64decode(hashed_password_encoded)

    # Calcular el hash usando scrypt con los mismos parámetros
    calculated_hash = scrypt.hash(input_password.encode('utf-8'), salt, N=N, r=r, p=p, buflen=buflen)

    # Verificar si el hash calculado coincide con el hash original
    return hashed_password == calculated_hash




