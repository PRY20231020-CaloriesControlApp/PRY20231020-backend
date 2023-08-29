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
import json
from decimal import Decimal
import numpy as np

PER_ETA = 0.10


def main(req: func.HttpRequest) -> func.HttpResponse:

    dia = req.get_json().get('dia')
    comida_del_dia = req.get_json().get('comida_del_dia')
    grupo_comida = req.get_json().get('grupo_comida')  
    input_username = req.get_json().get('user_name')
    input_person_id = req.get_json().get('person_id')
    token = req.get_json().get('token')

    conn_string = "dbname='postgres' user='pry20231020admin' host='pry20231020-db.postgres.database.azure.com' port='5432' password='P123456789**' sslmode='require'"

    connection_string = "DefaultEndpointsProtocol=https;AccountName=pry20231020fnb6cf;AccountKey=HFyQCPoYgeyOQgHupsGCSglXUq00E7m7q0+U3rPqPFnAjxWrl+jQ7Qd18S3tBKXUh6nTHVbhSThC+ASt8ju7nw==;EndpointSuffix=core.windows.net"
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client("pry20231020-dataset-ml")

    #file_name = container_client.get_blob_client("DatasetDesayuno.csv")
    if comida_del_dia == "Desayuno":
        file_name = container_client.get_blob_client("DatasetDesayuno.csv")
    elif comida_del_dia == "Almuerzo":
        file_name = container_client.get_blob_client("DatasetAlmuerzo.csv")
    elif comida_del_dia == "Cena":
          file_name = container_client.get_blob_client("DatasetCena.csv")

    blob = file_name.download_blob().readall().decode("utf-8")
    data = pd.read_csv(StringIO(blob))

    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()

    query = "SELECT session_authorization FROM session_authorization WHERE person_id = %s  order by date desc"
    valores = (input_person_id,)
    cursor.execute(query, valores) 
    row = cursor.fetchone()
    token02 = row[0]

    # Definir las columnas de características y la columna de etiqueta para el modelo
    columnas_caracteristicas = ["Edad", "Peso", "Altura", "Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo", "TipoLunes", "TipoMartes", "TipoMiercoles ", "TipoJueves", "TipoViernes", "TipoSabado", "TipoDomingo"]
    columna_etiqueta = dia

    # Filtrar los registros donde TipoLunes tiene valor 2
    tipodia ="TipoLunes"
    if dia == "Lunes":
        print("dia**" +dia)
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

    data_filtrada = data[data[tipodia] == grupo_comida]
  
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
    resultado_prediction = predictions[0]

    

    # Buscar detalles de la persona para calcular la cantidad de calorias que debe consumir durante el dia

    query = "SELECT  id, name, user_name, birth_date,gender, height, weight, activity_factor,caloric_reduction FROM person WHERE id = %s"
    valores = (input_person_id,)
    cursor.execute(query, valores) 
    row = cursor.fetchone()
    idperson = row[0]
    name = row[1]
    user_name = row[2]
    birth_date = row[3]
    gender = row[4]
    height = row[5]
    weight = row[6]
    activity_factor = row[7]
    caloric_reduction= row[8]

    #print("weight **************** "+ str(weight))

    #"Recommended" "Moderate" "Fast"

    age = calculate_age(birth_date)

    try:
        net = calculate_net(gender, weight, height, age, activity_factor)

        imc_value, imc_name, imc_scale = calculate_imc(height, weight)
        
        percentage_caloric_reduction = obtain_percentage_caloric_reduction (imc_scale, caloric_reduction)
        
        total_calories = calculate_total_calories(net, percentage_caloric_reduction)
    except ValueError as e:
        print("Error:", str(e))


    # Buscar la prediccion en la tabla Meal
    query = "SELECT id, name, type, healthy, healthy_equivalent_name, day_moment, recommended_id FROM public.meal WHERE recommended_id = %s and day_moment =%s "
    resultado1 = int(resultado_prediction)
    valores = (resultado1,comida_del_dia,)
    cursor.execute(query, valores) 
    row = cursor.fetchone()
    if row is not None:
        id_meal = row[0]
        name_meal = row[1]
        type_meal = row[2]
        is_healthy = row[3]
        healthy_equivalent_name = row[4]
        day_moment = row[5]
        recommended_id = row[6]
    else:
        # Handle the case when no row is fetched from the database
        # For example, you could set default values or raise an error
        id_meal = None
        name_meal = None
        type_meal = None
        is_healthy = None
        healthy_equivalent_name = None
        day_moment = None
        recommended_id = None

    query = "SELECT id, meal_id, name, weight, calories FROM public.healthy_meal_ingredient where  meal_id = %s  "
   
    resultado2 = int(id_meal)
    valores = (resultado2,)
    cursor.execute(query, valores) 
    rows = cursor.fetchall()


    # Crear un diccionario vacío para almacenar los ingredientes y sus macronutrientes
    ingredientes = {}

    # Recorrer los resultados de la consulta SQL
    count  = 0
    for row in rows:
        # Obtener la información de la fila
        ingredient_id = row[0]
        meal_id = row[1]
        ingredient_name = row[2]
        ingredient_weight = row[3]
        ingredient_calories = row[4]

       

        info_ingrediente = {
            'ingredient_name':ingredient_name,
            'ingredient_weight':float(ingredient_weight),
            'ingredient_calories': float(ingredient_calories)
        }
        ingredientes[ingredient_id] = info_ingrediente

    calories_meal_type=distribute_calories(total_calories,comida_del_dia)
    adjusted_ingredients = adjust_ingredient_quantities(ingredientes, calories_meal_type)
    


    data = {
        "id_person": input_person_id,
        "age": age,
        "gender": gender,
        "height": height,
        "weight": float(weight),
        "activity_factor": float(activity_factor),
        "imc": float(imc_value),
        "net": float(net),
        "total_calories": int(total_calories),  # Usamos el valor convertido a int
        "meal_day": comida_del_dia,
        "calories_meal_type": int(calories_meal_type),  # Usamos el valor convertido a int
        "meal_group": grupo_comida,
        "prediction_result": resultado_prediction,
        "id_meal": id_meal,
        "healthy_equivalent_name": healthy_equivalent_name,
        "token": token,
        "ingredients": []  # Creamos una lista vacía para los ingredientes
    }

    # Agregamos cada ingrediente a la lista "ingredients" en el diccionario "data"
    for ingredient_id, ingredient in adjusted_ingredients.items():
        ingredient_data = {
            "ingredient_name": ingredient['ingredient_name'],
            "ingredient_weight": float(ingredient['ingredient_weight']),
            "ingredient_calories": float(ingredient['ingredient_calories'])
        }
        data["ingredients"].append(ingredient_data)


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


def calculate_net(gender, weight, height, age, activity_factor):
    # Validate weight, height, and age inputs
    try:
        weight = float(weight)
        height = float(height)
        age = float(age)
    except ValueError:
        raise ValueError("El peso, altura y edad deben ser números válidos.")

    # Calculate TMB based on gender
    if gender == "M" :
        tmb = 10 * weight + 6.25 * height - 5 * age + 5
    else:  # "f" or "female"
        tmb = 10 * weight + 6.25 * height - 5 * age - 161

    print("tmb " + str(tmb))

    eta = tmb *PER_ETA
    print("PER_ETA " + str(PER_ETA))
    print("eta " + str(eta))
    print("activity_factor " + str(activity_factor))

    net = (tmb + eta)*float(activity_factor)
    print("net " + str(net))
    return net


def calculate_imc(height, weight):
    height_meters = height / 100 
    imc = float(weight) / (height_meters ** 2)

# Calcular IMC

    if imc < 18.5:
        return imc, "Bajo", 1
    elif 18.5 <= imc <= 24.9:
        return imc, "Normal", 2
    elif 25.0 <= imc <= 29.9:
        print("sobrepesoss")
        return imc, "Sobrepeso", 3
    elif 30.0 <= imc <= 34.9:
        return imc, "Obesidad I", 4
    elif 35.0 <= imc <= 39.9:
        return imc, "Obesidad II", 5
    else:
        print('return' , imc)
        return imc, "Obesidad III", 6
    

def obtain_percentage_caloric_reduction (imc_scale, caloric_reduction):
    speed="Normal"
    if caloric_reduction ==10:
        speed = "Lento"
    elif caloric_reduction ==15:
        print("Normal ******")
        speed = "Normal"
    elif caloric_reduction ==25:
        speed = "Rapido"

    percentage_caloric_reduction=0
    ## en caso de 1 bajo peso y 2 normal - a partir del 3 tiene sobrepeso
    if imc_scale ==1:
        if speed == "Lento":
            percentage_caloric_reduction = 0
        elif speed == "Normal":  
            percentage_caloric_reduction = 0
        elif speed == "Rapido":  
            percentage_caloric_reduction = 0
    elif imc_scale ==2:
        if speed == "Lento":
            percentage_caloric_reduction = 5
        elif speed == "Normal":  
            percentage_caloric_reduction = 10
        elif speed == "Rapido":  
            percentage_caloric_reduction = 15
    elif imc_scale ==3:
        if speed == "Lento":
            percentage_caloric_reduction = 10
        elif speed == "Normal":  
            percentage_caloric_reduction = 15
        elif speed == "Rapido":  
            percentage_caloric_reduction = 25
    elif imc_scale ==4:
        if speed == "Lento":
            percentage_caloric_reduction = 10
        elif speed == "Normal":  
            percentage_caloric_reduction = 15
        elif speed == "Rapido":  
            percentage_caloric_reduction = 25
    elif imc_scale ==5:
        if speed == "Lento":
            percentage_caloric_reduction = 10
        elif speed == "Normal":  
            percentage_caloric_reduction = 15
        elif speed == "Rapido":  
            percentage_caloric_reduction = 25
    elif imc_scale ==6:
        if speed == "Lento":
            percentage_caloric_reduction = 10
        elif speed == "Normal":  
            percentage_caloric_reduction = 15
        elif speed == "Rapido":  
            percentage_caloric_reduction = 25

    return percentage_caloric_reduction

def calculate_total_calories(net, percentage_caloric_reduction):
    if percentage_caloric_reduction != 0:
        calorie_reduction = float(net) * (percentage_caloric_reduction/100)
        total_calories = round(net - calorie_reduction)
        return total_calories
    else:
       return round(net)
    
def distribute_calories(total_calories, meal_type):
    breakfast_calories = round(total_calories * 0.25)
    lunch_calories = round(total_calories * 0.50)
    dinner_calories = total_calories - breakfast_calories - lunch_calories
    
    if meal_type == 'Desayuno':
        calories_meal_type=breakfast_calories
    elif meal_type == 'Almuerzo':
        calories_meal_type=lunch_calories
    else:
        calories_meal_type=dinner_calories
    return calories_meal_type
    

def adjust_ingredient_quantities(ingredients, target_calories):
    original_calories = sum(ingredient['ingredient_calories'] for ingredient in ingredients.values())

    for ingredient_id, ingredient in ingredients.items():
        original_calories_ingredient = ingredient['ingredient_calories']
        original_weight_ingredient =ingredient['ingredient_weight'] 
        new_quantity = (ingredient['ingredient_weight'] * target_calories) / original_calories
        ingredients[ingredient_id]['ingredient_weight'] = round(new_quantity)  
        ingredients[ingredient_id]['ingredient_calories'] = round((original_calories_ingredient * new_quantity) / original_weight_ingredient, 1)
    return ingredients







