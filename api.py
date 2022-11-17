#Librerias necesarias para la conexion de la api con la base de datos
#os y dotenv los usamos para obtener la informacion del inicio de sesion
import os
from dotenv import load_dotenv, find_dotenv

#Librerias de Flask y Mongo
from flask import Flask, request
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from flask_cors import CORS

# flask --app EnsenaAPI.py run

#Librerias para la logica de la api
import random as rd
from operator import itemgetter

#Tomamos las variables del .env y las guardamos
load_dotenv(find_dotenv())
username = os.environ.get('USER') #Usuario de la base de datos
password = os.environ.get('PASSWORD') #Contraseña para la base de datos

app = Flask(__name__) #Inicializamos Flask
CORS(app) #Habilitamos las rutas

#Conectamos con el ID de nuestra base de datos (los datos de inicio de sesion no son visibles porque estan en el .env) 
app.config['MONGO_URI'] = 'mongodb+srv://root:accessToData2@practicedatabases.n4dtxaz.mongodb.net/Ensena'

mongo = PyMongo(app) #En esta variable guardamos el acceso a la base de datos

#Estas son las llamadas a la base de datos

#-----------------------------------Rutas para usuarios------------------------------------------------------

#Se obtiene la informacion de un usuario dado su username
@app.route('/user/all', methods=['GET'])
def getAlUsers():
    #Hacemos el query de todos los usuarios y regresamos su id, nombre, apellido, puesto y las calificaciones.
    users = mongo.db.Users.find({}, {'_id': 1, 'name': 1, 'lastname': 1, 'position': 1, 'courses': 1})
    if(users == None): #Verificamos que la respuesta no venga vacia
        #Si esta vacia mandamos un error de que no hay usuarios
        return {
            'error': 'No se encontraron usuarios en la base de datos'
        }
    
    #Creamos una lista donde guardamos todos los usuarios que recibimos de respuesta
    list = []
    for user in users:
        #Convertimos el id de Mongo a string para poder mandarlo como json
        user['_id'] = str(user['_id'])
        list.append(user) #Guardamos los usuarios en la lista

    #Mandamos la lista con el nombre de 'usuarios'
    dictionary = {'user': list}
    return dictionary



#Se obtiene la informacion de un usuario dado su id
@app.route('/user/<_id>/info', methods=['GET'])
def findUser(_id):
    objID = ObjectId(_id) #Convertimos el id al objeto de mongo
    user = mongo.db.Users.find_one({'_id': objID}) #Obtenemos la informacion del usuario
    courses = mongo.db.Courses.find({}, {'_id': 1}) #Obtenemos una lista de los ids de los cursos que existen (se usa para saber el progreso del usuario)

    #Verificamos que exista un usuario
    if (user == None):
        return {'error': 'Usuario no encontrado'}

    #Calculamos el progreso del usuario dividiendo los cursos que tiene entre todos los que existen
    totalCourses = len(list(courses))
    userCourses = len(user['courses'])
    progress = int(userCourses / totalCourses * 100)

    #Creamos una lista con los nombres de los cursos que el usuario ha completado
    listCourses = []
    for course in user['courses']:
        listCourses.append(course['title'])

    #Retornamos la infomacion del usuario
    return {'fullName': user['name'] + ' ' + user['lastname'],
            'position': user['position'],
            'courseProgress': progress,
            'completedCourses': listCourses
            }



#Se usa para obtener la informacion de la pantalla de administrador dado su id
@app.route('/user/admin/<_id>/info', methods=['GET'])
def findAdmin(_id):
    objID = ObjectId(_id) #Convertimos el id a un objeto de mongo
    user = mongo.db.Users.find_one({'_id': objID}) #Obtenemos la informacion del usuario admin
    users = mongo.db.Users.find({}, {'name': 1, 'lastname': 1, 'courses': 1}) #Obtenemos la informacion de todos los usuarios registrados
    courses = mongo.db.Courses.find({}, {'_id': 1}) #Obtenemos la cantidad de cursos que existen para calcular el progreso de cada usuario

    #Verificamos que el usuario admin exista
    if (user == None):
        return {'error': 'Usuario no encontrado'}

    #Calculamos la cantidad de cursos que tenemos registrados
    totalCourses = len(list(courses))

    #Creamos una lista para guardar la informacion de todos los usuarios
    usersList = []
    for u in users:
        #Intentamos obtener la informacion de la cantidad de cursos que ha aprobado el usuario
        try:
            #Si existe lo guardamos para hacer el calculo
            userCourses = len(u['courses'])
        except:
            #Si no existe es porque es admin e ignoramos a este usuario
            continue
        
        #Calculamos el progreso del usuario
        progress = int(userCourses / totalCourses * 100)

        #Guardamos al usuario con su informacion en la lista de usuarios
        usersList.append({
            'fullName': u['name'] + ' ' + u['lastname'],
            'courseProgress': progress
        })

    #Retornamos la informacion de los usuarios y el nombre del admin
    return {
        'fullName': user['name'] + ' ' + user['lastname'],
        'numUsers': str(len(usersList)),
        'userList': usersList
    }




#Esta ruta se usa para validar el login de un usuario y decir si es admin o no
@app.route('/user/login/', methods=['POST'])
def login():
    #Usamos el body para los parametros porque son sensibles y tambien porque queremos que sean case sensitive (mientras no los mandamos con la app en hash)
    username = request.json['username'] #Obtenemos el usuario que viene en el body
    password = request.json['password'] #Obtenemos la contrasenia que viene del body
    user = mongo.db.Users.find_one({'username': username, 'password': password}, {'_id': 1, 'type': 1}) #Buscamos un usuario con ese usuario y contraseñnia

    #Si el resultado de la busqueda viene vacio quiere decir que el usuario no existe
    if(user == None):
        #Retornamos un login falso
        return {'login': False}

    #Verificamos si es un usuario admin
    isAdmin = False
    try:
        #Si tiene atributo type y es igual a admin, entonces es un admin
        if user['type'] == "admin":
            isAdmin = True
    except:
        #Si no existe el atributo continuamos
        isAdmin = False

    #Retornamos la informacion del login exitoso
    return {
        'login': True,
        'userId': str(user['_id']),
        'admin': isAdmin
    }
    
#Esta ruta se utiliza para actualizar la calificacion de un usuario
@app.route('/user/update/grade', methods=['PUT'])
def updateGrade():
    #Obtenemos los cursos que ya tenia el usuario
    userID = ObjectId(request.json['_id'])
    userCourses = mongo.db.Users.find_one({"_id": userID}, {"courses" : 1})

    #Obtenemos la informacion a ser actualizada
    course = request.json['course']
    newGrade = int(request.json['grade'])
    

    #Guardamos los cursos en una lista
    cursos = userCourses['courses']
    updated = False
    for c in cursos:
        if c['title'].lower() == course.lower():
            if int(c['grade']) < newGrade:
                c['grade'] = newGrade
            
            updated = True
            break

    if not updated:
        cursos.append({
            'title': course,
            'grade': newGrade
        })
    
    mongo.db.Users.update_one({"_id" : userID} , { "$set": {"courses": cursos}})

    return {"status": "success",
        "course": course,
    }

#-------------------------------------------------Rutas para los cursos-----------------------------------------------

#Retorna la informacion para la parte principal de los cursos (cuando el usuario esta desloggeado)
@app.route('/course/all', methods=['GET'])
def getCoursesNames():
    #Hacemos el query con id, titulo y modulo para los cursos
    courses = mongo.db.Courses.find({}, {'_id': 1, 'title': 1, 'image': 1})
    if(courses == None): #Verificamos que la respuesta no venga vacia
        return {
            'error': 'No se encontraron usuarios en la base de datos'
        }

    #Guardamos los cursos en la lista
    list = []
    for course in courses:
        course['_id'] = str(course['_id']) #Convertimos el objeto de id a string

        #Creamos un objeto de nuevo curso para mandarlo
        #Como esta ruta se usa para los cursos cuando un usuario no esta loggeado, mandamos los datos que no existen con -1 
        newCourse = {
            'id': course['_id'],
            'name': course['title'],
            'maxGrade': str(-1),
            'grade': str(-1),
            'image': course['image']
            }
        list.append(newCourse)

    #Retornamos la lista de los cursos
    return dict({'courses': list})



#Se usa para la lista de cursos cuando un usuario con _id esta loggeado (se cargan tambien sus calificaciones)
@app.route('/course/all/<_id>', methods=['GET'])
def getCoursesGrades(_id):
    #Hacemos el query con id, titulo y modulo para los cursos
    courses = mongo.db.Courses.find({}, {'_id': 1, 'title': 1, 'image': 1, 'content': 1})
    
    #Hacemos un query para saber los cursos que ha completado el usuario con el _id
    objID = ObjectId(_id)
    user = mongo.db.Users.find_one({'_id': objID}, {'courses': 1})
    if(courses == None): #Verificamos que la respuesta no venga vacia
        return {
            'error': 'No se encontraron usuarios en la base de datos'
        }
    elif(user == None):
        return {
            'error': 'No se encontro un usuario con el id dado'
        }
        

    #Guardamos los cursos en la lista
    courseInfo = []
    for course in courses:
        course['_id'] = str(course['_id']) #Convertimos el objeto de id a un string

        #Inicializamos la calificacion del curso en 0 (porque si no existe en los cursos del usuario quiere decir que no lo ha completado)
        grade = 0
        for userCourse in user['courses']:
            #Encontramos la calificacion que tiene ese usuario en ese curso (si no existe se queda en 0)
            if course['title'] == userCourse['title']:
                #Actualizamos la calificacion
                grade = userCourse['grade']
                break

        #Guardamos la informacion del curso, con la calificacion que el usuario tiene y la calificacion maxima del curso
        newCourse = {
            'id': course['_id'],
            'name': course['title'],
            'maxGrade': str(len(list(course['content']))),
            'grade': str(grade),
            'image': course['image']
            }
        courseInfo.append(newCourse)

    #Retornamos la lista con los cursos
    return dict({'courses': courseInfo})



#Esta ruta se usa para obtener la lista de palabras con sus gifs de un curso con un id dado
@app.route('/course/<_id>/learn', methods=['GET'])
def courseLearn(_id):
    #Hacemos el query buscando el curso con el id que recibimos
    objID = ObjectId(_id)
    course = mongo.db.Courses.find_one({'_id': objID}, {'content': 1})
    
    #Verificamos que exista el curso que buscamos
    if(course == None): #Verificamos que la respuesta no venga vacia
        return {
            'error': 'No se encontraron preguntas para el curso'
        }
    
    #Creamos una lista en donde vamos a guardar todas las palabras del curso
    list = []
    for word in course['content']:
        list.append(word)
    
    #Retornamos las palabras del curso
    #Pendiente de ver como manejar los links para los gifs
    return dict({'wordList': list})



#Ruta que se usa para obtener preguntas sobre las palabras del curso con id dado
@app.route('/course/<_id>/practice', methods=['GET'])
def coursePractice(_id):
    #Hacemos un query con el id del curso
    objID = ObjectId(_id)
    course = mongo.db.Courses.find_one({'_id': objID}, {'content': 1})

    #Verificamos que el curso exista
    if(course == None):
        return {
            'error': 'No se encontraron preguntas para el curso'
        }

    #Creamos una lista donde vamos a guardar todas las preguntas
    questionList = []
    cantPalabras = len(course['content'])
    for i in range(cantPalabras):
        #Generamos el objeto donde se guardara cada pregunta
        pregunta = {'correct': course['content'][i]['word'],
                    'url': course['content'][i]['url'],
                    'incorrectList': [],
                    'type': 'Multiple choice'}

        #Las siguientes listas y while se usa para escoger aleatoriamente 3 de las demas palabras y usarlas como respuestas incorrectas
        count = 0 #Contamos cuantas repuestas incorctas hemos guardado
        incorrectAns = [] #Guardamos los strings de las respuestas incorrectas
        incorrectIndex = [] #Guardamos las respuestas incorrectas para no repetir
        incorrectIndex.append(i) #Guardamos la palabra correcta como incorrecta para no seleccionarla en las respuestas incorrectas
        while count < 3:
            #Generamos un numero aleatorio y si no ha sido seleccionado la ponemos como la palabra incorrecta
            j = rd.randint(0, cantPalabras - 1)
            if j in incorrectIndex:
                continue
            incorrectAns.append(course['content'][j]['word'])
            incorrectIndex.append(j)
            count += 1
        
        #Guardamos las palabras incorrectas en el objeto de pregunta
        pregunta['incorrectList'].append(incorrectAns)
        questionList.append(pregunta) #Guardamos la pregunta en la lista de preguntas

    #Revolvemos las preguntas
    rd.shuffle(questionList)
    #Retornamos la lista generada con preguntas
    return dict({'questionList': questionList})


#Ruta que se usa para obtener preguntas sobre las palabras del modulo con un numero de modulo dado
@app.route('/course/module/<num>/practice', methods=['GET'])
def moduleQuestions(num):
    #Hacemos un query con el numero del modulo
    courses = mongo.db.Courses.find({'module': int(num)}, {'content': 1})

    #Verificamos que el curso exista
    if(courses == None):
        return {
            'error': 'No se encontraron preguntas para el modulo ' + num 
        }

    cantPalabras = 0
    #Creamos un array con todas las palabras del modulo
    words = []
    for course in courses:
        for word in course['content']:
            words.append(word)
            cantPalabras += 1

    cantPreguntas = 6 #Lo usamos para determinar la cantidad de preguntas que se van a generar
    #De ahi elegimos de forma random palabras para que sean las respuestas correctas
    correct = []
    correctIndex = []
    correctCount = 0
    while correctCount < cantPreguntas:
            #Generamos un numero aleatorio y si no ha sido seleccionado la ponemos como la palabra incorrecta
            j = rd.randint(0, cantPalabras - 1)
            if j in correctIndex:
                continue
            correct.append(words[j])
            correctIndex.append(j)
            correctCount += 1

    
    #Creamos una lista donde vamos a guardar todas las preguntas
    questionList = []
    for i in range(cantPreguntas):
        #Generamos el objeto donde se guardara cada pregunta
        pregunta = {'correct': correct[i]['word'],
                    'url': correct[i]['url'],
                    'incorrectList': [],
                    'type': 'Multiple choice'}

        #Las siguientes listas y while se usa para escoger aleatoriamente 3 de las demas palabras y usarlas como respuestas incorrectas
        count = 0 #Contamos cuantas repuestas incorctas hemos guardado
        incorrectAns = [] #Guardamos los strings de las respuestas incorrectas
        incorrectIndex = [] #Guardamos las respuestas incorrectas para no repetir (las guardamos como string)
        incorrectIndex.append(correct[i]['word']) #Guardamos la palabra correcta como incorrecta para no seleccionarla en las respuestas incorrectas
        while count < 3:
            #Generamos un numero aleatorio y si no ha sido seleccionado la ponemos como la palabra incorrecta
            j = rd.randint(0, cantPalabras - 1)
            if words[j]['word'] in incorrectIndex:
                continue
            incorrectAns.append(words[j]['word'])
            incorrectIndex.append(words[j]['word'])
            count += 1
        
        #Guardamos las palabras incorrectas en el objeto de pregunta
        pregunta['incorrectList'].append(incorrectAns)
        questionList.append(pregunta) #Guardamos la pregunta en la lista de preguntas

    #Revolvemos las preguntas
    rd.shuffle(questionList)
    #Retornamos la lista generada con preguntas
    return dict({'questionList': questionList})


# ---------------------------------------------------- Ruta para diccionarios ----------------------------------------------------------

#Esta ruta se usa para acceder a todas las palabras guardadas de todos los cursos
@app.route('/dictionary', methods=['GET'])
def getDictonary():
    #Obtenemos la informacion de todos los cursos
    courses = mongo.db.Courses.find({}, {'_id': 1, 'title': 1, 'image': 1, 'content': 1})
    if(courses == None): #Verificamos que la respuesta no venga vacia
        return {
            'error': 'No hay palabras en el diccionario'
        }

    #Creamos una lista para guardar todas las palabras
    wordsList = []

    #Iteramos todos los cursos
    for course in courses:
        #Iteramos todas las palabras del curso
        for word in course['content']:
            #Creamos el diccionario con la informacion que se necesita para cada palabra
            objWord = {
                'image': course['image'],
                'name': word['word'],
                'courseName': course['title'],
                'courseId': str(course['_id'])
            }
            #Metemos el diccionario a la lista
            wordsList.append(objWord)

    #Retornamos la lista de palabras
    return dict({'resultList': sorted(wordsList, key=itemgetter('name'))})

if __name__ == "_main_":
    app.run(debug=True) #Con el True en debug se reinicia cuando hay cambios
