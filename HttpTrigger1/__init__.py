import psycopg2
import pandas as pd
import azure.functions as func
from io import StringIO
from azure.storage.blob import BlobServiceClient
import joblib
from sklearn import svm
import os
import tempfile
from datetime import datetime
#import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    conn_string = "dbname='postgres' user='pry20231020admin' host='pry20231020-db.postgres.database.azure.com' port='5432' password='P123456789**' sslmode='require'"

    connection_string = "DefaultEndpointsProtocol=https;AccountName=pry20231020fnb6cf;AccountKey=HFyQCPoYgeyOQgHupsGCSglXUq00E7m7q0+U3rPqPFnAjxWrl+jQ7Qd18S3tBKXUh6nTHVbhSThC+ASt8ju7nw==;EndpointSuffix=core.windows.net"
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client("pry20231020-dataset-ml")

    file_name = container_client.get_blob_client("dataset_prueba.csv")
    blob = file_name.download_blob().readall().decode("utf-8")
    data = pd.read_csv(StringIO(blob))

    dia = req.get_json().get('dia')
    tipoComida = req.get_json().get('tipoComida')
    token = req.get_json().get('token')
    input_username = req.get_json().get('user_name')

    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    query = "SELECT id FROM person WHERE user_name = %s"
    valores = (input_username,)
    cursor.execute(query, valores) 
    row = cursor.fetchone()
    personid = row[0]

    query = "SELECT session_authorization FROM session_authorization WHERE person_id = %s  order by date desc"
    valores = (personid,)
    cursor.execute(query, valores) 
    row = cursor.fetchone()
    token02 = row[0]

    # Definir las columnas de características y la columna de etiqueta para el modelo
    columnas_caracteristicas = ["Edad", "Peso", "Altura", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo", "TipoLunes", "TipoMartes", "TipoMiercoles ", "TipoJueves", "TipoViernes", "TipoSabado", "TipoDomingo"]
    columna_etiqueta = dia

    # Filtrar los registros donde TipoLunes tiene valor 2
    tipodia ="TipoLunes"
    if dia == "Lunes":
        tipodia="TipoLunes"
    elif dia == "Martes":
        tipodia="TipoMartes"
    elif dia == "Miercoles":
        tipodia="TipoMiercoles"
    elif dia == "Jueves":
        tipodia="TipoJueves"
    elif dia == "Viernes":
        tipodia="TipoViernes"
    elif dia == "Sabado":
        tipodia="TipoSabado"
    else:
        tipodia="TipoDomingo"

    data_filtrada = data[data[tipodia] == tipoComida]
  
    # Obtener los datos de características (X) y etiquetas (y) del dataset
    X = data_filtrada[columnas_caracteristicas]
    y = data_filtrada[columna_etiqueta]

    # Crear y entrenar el modelo SVM
    modelo_entrenado = svm.SVC()
    modelo_entrenado.fit(X, y)

    # Guardar el modelo entrenado en un archivo .pkl
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, "modelo_entrenado.pkl")
    joblib.dump(modelo_entrenado, temp_file)

    # Crear un DataFrame con los datos de entrada para la predicción
    input_data = pd.DataFrame([[30, 85, 170, 37, 10, 18, 34, 9, 23, 1,1,1,1,1,1,1,1]], columns=columnas_caracteristicas)

    # Realizar la predicción utilizando el modelo entrenado
    predictions = modelo_entrenado.predict(input_data)

    # Obtener el resultado de la predicción
    resultado = predictions[0]

    # Buscar detalles de la persona para calcular la cantidad de calorias que debe consumir durante el dia

    query = "SELECT  id, name, user_name, birth_date,gender, height, weight, activity_level FROM person WHERE user_name = %s"
    valores = (input_username,)
    cursor.execute(query, valores) 
    row = cursor.fetchone()
    idperson = row[0]
    name = row[1]
    user_name = row[2]
    birth_date = row[3]
    gender = row[4]
    height = row[5]
    weight = row[6]
    activity_level = row[7]
    speed = "Recommended"
    #"Recommended" "Moderate" "Fast"

    age = calculate_age(birth_date)

    # Calcular tasa de metabolismo basal (TMB) 
    imc, message, scale = calculate_imc(height, weight)
    print('***scale ', scale)

    # Calcular Porcentaje de reduccion calorica  
    percentage_caloric_reduction = obtain_percentage_caloric_reduction (scale, speed)
   
    # Calcular tasa de metabolismo basal (TMB) 
    tmb = calculate_tmb(gender, weight, height, age, activity_level)
    print("TMB:", tmb)
    
    calories_limit = calculate_calorie_range(tmb, percentage_caloric_reduction)
    
    #calcular cuantos macronutrientes se necesitan por comida
    protein_grams,protein_kcal, fat_grams, fat_kcal, carb_kcal, carb_grams= calculate_macronutrients(3,weight,calories_limit)

    # Buscar la prediccion en la tabla Meal
    query = "SELECT id, name, type, healthy, healthy_equivalent_name, day_moment FROM public.meal WHERE id = %s "
    resultado = int(resultado)
    valores = (resultado,)
    cursor.execute(query, valores) 
    row = cursor.fetchone()
    id_meal = row[0]
    name_meal = row[1]
    type_meal = row[2]
    is_healthy = row[3]
    healthy_equivalent_name = row[4]
    day_moment = row[5]


    query = "SELECT id, ingredient, macronutrient_id, calories_per_100g FROM public.healthy_meal_ingredient WHERE meal_id = %s and macronutrient_id = 1 "
    resultado = int(id_meal)
    valores = (id_meal,)
    cursor.execute(query, valores) 
    rows = cursor.fetchall()

    ingredient_proteins = None
    ingredient_fats = None
    ingredient_carbs = None
    for row in rows:
        id_ingredient = row[0]
        ingredient = row[1]
        macronutrient_id = row[2]
        calories_per_100g = row[3]

        if macronutrient_id == 1: #Carbohidratos
            id_ingredient_carbs = id_ingredient
            ingredient_carbs = ingredient
            calories_per_100g_carbs = calories_per_100g
        elif macronutrient_id == 2: #Proteina
            id_ingredient_proteins = id_ingredient
            ingredient_proteins = ingredient
            calories_per_100g_proteins= calories_per_100g
        elif macronutrient_id == 3: #Grasa
            id_ingredient_fats = id_ingredient
            ingredient_fats = ingredient
            calories_per_100g_fats= calories_per_100g



    data = {
        "idPerson": personid,
        "age": age,
        "gender":gender,
        "height":height,
        "weight":float(weight),
        "activity_level":activity_level,
        "speed":speed,
        "percentage_caloric_reduction":percentage_caloric_reduction,
        "imc": float(imc),
        "tmb": tmb,
        "calories_limit": calories_limit,
        "prediction_result": resultado,
        "healthy_equivalent_name": healthy_equivalent_name,
        "protein_grams": protein_grams,
        "protein_kcal": protein_kcal,
        "fat_grams": fat_grams,
        "fat_kcal": fat_kcal,
        "carb_kcal": carb_kcal,
        "carb_grams": carb_grams,
        "ingredient_carbs": ingredient_carbs,
        "ingredient_proteins": ingredient_proteins,
        "ingredient_fats": ingredient_fats,
        "token": token
    }

    #return func.HttpResponse(json.dumps(data), mimetype="application/json")

    response_data = "{\n"
    for key, value in data.items():
        response_data += f'    "{key}": {repr(value)},\n'
    response_data += "}"

    return func.HttpResponse(response_data, mimetype="application/json")

    # Obtener el valor del parámetro 'name' de la solicitud HTTP
    """
        pd.set_option('max_columns', None)
    pd.set_option('max_rows', None)

    if dia:
        return func.HttpResponse(f"TMB {tmb} {birth_date}  holi {age} {tmb} Lista de recomendaciones por {dia}. Resultado de la predicción: {resultado}. \n Data Filtrada. \n {data_filtrada}. \n personid: {personid} \n token {token} ")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
    """

def calculate_age (birth_date):  
    fecha_actual = datetime.now()
    age = fecha_actual.year - birth_date.year
    if fecha_actual.month < birth_date.month:
        age -= 1
    elif fecha_actual.month == birth_date.month and fecha_actual.day < birth_date.day:
        age -= 1
    return age

def calculate_imc(height, weight):
    height_meters = height / 100 
    imc = float(weight) / (height_meters ** 2)

# Calcular IMC

    if imc < 18.5:
        return imc, "Tienes un IMC bajo. Por favor, consulta a un profesional de la salud antes de utilizar esta aplicación.", 1
    elif 18.5 <= imc <= 24.9:
        print('imc 18.5 <= imc <= 24.9' , imc)
        return imc, "Tu IMC es normal. Puedes utilizar esta aplicación según tus necesidades y preferencias.", 2
    elif 25.0 <= imc <= 29.9:
        return imc, "Tienes sobrepeso. Se recomienda utilizar esta aplicación bajo el asesoramiento de un profesional de la salud.", 3
    elif 30.0 <= imc <= 34.9:
        return imc, "Tienes obesidad de grado I. Se recomienda utilizar esta aplicación bajo el asesoramiento de un profesional de la salud.", 4
    elif 35.0 <= imc <= 39.9:
        return imc, "Tienes obesidad de grado II. Se recomienda utilizar esta aplicación bajo el asesoramiento de un profesional de la salud.", 5
    else:
        print('return' , imc)
        return imc, "Tienes obesidad de grado III. Se recomienda utilizar esta aplicación bajo el asesoramiento de un profesional de la salud.", 6


def obtain_percentage_caloric_reduction (scale, speed):
    percentage_caloric_reduction=0
    if scale ==1:
        if speed == "Recommended":
            percentage_caloric_reduction = 0
        elif speed == "Moderate":  
            percentage_caloric_reduction = 0
        elif speed == "Fast":  
            percentage_caloric_reduction = 0
    elif scale ==2:
        if speed == "Recommended":
            percentage_caloric_reduction = 10 #0
        elif speed == "Moderate":  
            percentage_caloric_reduction = 10
        elif speed == "Fast":  
            percentage_caloric_reduction = 10   
    elif scale ==3:
        if speed == "Recommended":
            percentage_caloric_reduction = 10
        elif speed == "Moderate":  
            percentage_caloric_reduction = 10
        elif speed == "Fast":  
            percentage_caloric_reduction = 20  
    elif scale ==4:
        if speed == "Recommended":
            percentage_caloric_reduction = 10
        elif speed == "Moderate":  
            percentage_caloric_reduction = 10
        elif speed == "Fast":  
            percentage_caloric_reduction = 20  
    elif scale ==5:
        if speed == "Recommended":
            percentage_caloric_reduction = 10
        elif speed == "Moderate":  
            percentage_caloric_reduction = 20
        elif speed == "Fast":  
            percentage_caloric_reduction = 30 
    elif scale ==6:
        if speed == "Recommended":
            percentage_caloric_reduction = 10
        elif speed == "Moderate":  
            percentage_caloric_reduction = 20
        elif speed == "Fast":  
            percentage_caloric_reduction = 30

    return percentage_caloric_reduction

def calculate_tmb(gender, weight, height, age, activity_level):
    weight = float(weight)
    height = float(height)
    age = float(age)
    
    if gender == "M":
        tmb = (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif gender == "F":
        tmb = (10 * weight) + (6.25 * height) - (5 * age) - 161
    else:
        raise ValueError("Invalid gender. Expected 'male' or 'female'.")
    
    activity_levels = {
        1: 1.2,
        2: 1.375,
        3: 1.55,
        4: 1.725,
        5: 1.9
    }
    activity_level = activity_levels.get(activity_level, 1.2)  # Valor predeterminado es 1.0 si la opción no existe

    tmb *= activity_level
    #tmb = round(tmb)  # Redondear el valor del TMB a un número entero

    return tmb

def calculate_calorie_range(tmb, percentage_caloric_reduction):
    if percentage_caloric_reduction != 0:
        calorie_reduction = tmb * (percentage_caloric_reduction / 100)
        calories_limit = tmb - calorie_reduction
        return calories_limit
    else:
       return tmb 

def calculate_macronutrients(number_meals, weight, calories_limit, protein_g=2.5, fat_g=0.8):
    # Cálculo de proteína
    protein_grams = (float(protein_g) * float(weight)) #/ number_meals
    protein_kcal = (protein_grams * 4) #/number_meals

    # Cálculo de grasa
    fat_grams = (float(fat_g) * float(weight)) #/number_meals
    fat_kcal = (fat_grams * 9) #/number_meals

    # Cálculo de carbohidrato
    carb_kcal = (calories_limit - (protein_kcal + fat_kcal)) #/number_meals
    carb_grams = (carb_kcal / 4) #/number_meals

    protein_grams = protein_grams/number_meals
    protein_kcal=protein_kcal/number_meals

    fat_grams=fat_grams/number_meals
    fat_kcal=fat_kcal/number_meals

    carb_kcal=carb_kcal/number_meals
    carb_grams=carb_grams/number_meals

    return protein_grams,protein_kcal, fat_grams, fat_kcal, carb_kcal, carb_grams
    
 