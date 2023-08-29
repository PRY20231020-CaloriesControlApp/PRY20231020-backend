import psycopg2
import azure.functions as func
import scrypt 

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime
import numpy as np



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
            
            """
             query = "SELECT id FROM person WHERE user_name = %s"
            valores = (input_username,)
            cursor.execute(query, valores) 
            row = cursor.fetchone()
            personid = row[0]
            """
            query = "SELECT  id, name, user_name, birth_date,gender, height, weight, activity_factor,caloric_reduction, registration_date FROM person WHERE user_name = %s"
            valores = (input_username,)
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
            registration_date = row[9]

            print("LOGIN weight **************** "+ str(weight))

            

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


            query = " SELECT DISTINCT ON (consumed_date) id, person_id, consumed_date, consumed_calories, weight FROM public.person_history WHERE person_id = %s ORDER BY consumed_date DESC, id DESC "
            valores = (personid,)
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
                progress_weight = row[4]

            

                info_progress= {
                    'progress_id':progress_id,
                    'person_id':person_id,
                    'consumed_date': consumed_date.isoformat(),
                    'consumed_calories': consumed_calories,
                    'progress_weight': float(progress_weight)
                }
                progress[progress_id] = info_progress

            
      
            conn.commit()

            conn.close()
            age = calculate_age(birth_date)
            registration_date_str = registration_date.isoformat()


            birth_date_str = birth_date.isoformat()

            data = {
                "id_person": personid,
                "user_name": input_username,
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
                "token": token,
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




def calculate_age (birth_date):  
    fecha_actual = datetime.now()
    age = fecha_actual.year - birth_date.year
    if fecha_actual.month < birth_date.month:
        age -= 1
    elif fecha_actual.month == birth_date.month and fecha_actual.day < birth_date.day:
        age -= 1
    return age