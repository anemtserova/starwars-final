"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Favorite
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
import datetime
#from models import Person
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret" # Change this!
jwt = JWTManager(app)


app.url_map.strict_slashes = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_CONNECTION_STRING')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)

@app.route('/bear', methods=['GET'])
@jwt_required() 
def handle_bear(): 
    current_user_id = get_jwt_identity()
    user = User.filter.get(current_user_id)
    
    return jsonify({"id": user.id, "username": user.username }), 200

@app.route("/login", methods=["POST"])
def create_token():
    credentials = request.get_json()
    username = credentials.get("username", None)
    password = credentials.get("password", None)
    # Query your database for username and password
    user = User.query.filter_by(username=username, password=password).first()
    if user is None:
        # the user was not found on the database
        return jsonify({"msg": "Invalid username or password"}), 401
    
    # create a new token with the user id inside
    expires = datetime.timedelta(days=7)
    access_token = create_access_token(identity=user.username,expires_delta=expires)
    return jsonify({ "token": access_token, "user_id": user.username })

@app.route('/user', methods=['GET'])
def handle_hello():
    all_users = User.query.all()
    all_users = list(map(lambda elem: elem.serialize(), all_users))
    response_body = {
        "users": all_users
    }

    return jsonify(response_body), 200

@app.route('/<user>/favorites', methods=['GET'])
def getFavorites(user):
    single_user = User.query.filter_by(username=user).first()
    if single_user is None:
        raise APIException('User not found', status_code=404) 
    favorites = Favorite.query.filter_by(username=user)
    all_favorites = list(map(lambda elem: elem.serialize(), favorites))
    response_body = {
        "all_favorites": all_favorites
    }

    return jsonify(response_body), 200

@app.route('/favorite/planet/<int:id>', methods=['POST', 'DELETE'])

def addPlanet(id):
    request_body = request.get_json()
    if request_body is None or request_body == {}:
        raise APIException('Data not found', status_code=404)
    if request.method == 'POST':
        planet = Favorite(name=request_body['name'], entity_type='planet', entity_id=id, username=request_body['username'])
        db.session.add(planet)
        db.session.commit()
    if request.method == 'DELETE':
        planetRemoved = Favorite.query.filter_by( entity_type='planet', entity_id=id, username=request_body['username']).first()
        # if planetRemoved is None:
        #     raise APIException('Planet not found', status_code=404)  
        db.session.delete(planetRemoved)
        db.session.commit()
    favorites = Favorite.query.filter_by(username=request_body['username'])
    all_favorites=list(map(lambda elem: elem.serialize(), favorites))
    response_body = {
        "favorites": all_favorites
    }

    return jsonify(response_body), 200


@app.route('/favorite/people/<int:id>', methods=['POST', 'DELETE'])

def addPerson(id):
    request_body = request.get_json()
    if request_body is None or request_body == {}:
        raise APIException('Data not found', status_code=404)
    if request.method == 'POST':
        record = Favorite.query.filter_by(username=request_body['username'], name=request_body['name']).first()
        if record:
            raise APIException('Duplicate record found', status_code=418)
        person = Favorite(name=request_body['name'], entity_type='person', entity_id=id, username=request_body['username'])
        db.session.add(person)
        db.session.commit()
    if request.method == 'DELETE':
        personRemoved = Favorite.query.filter_by( entity_type='person', entity_id=id, username=request_body['username']).first()
        # if personRemoved is None:
        #     raise APIException('person not found', status_code=404)  
        db.session.delete(personRemoved)
        db.session.commit()
    favorites = Favorite.query.filter_by(username=request_body['username'])
    all_favorites=list(map(lambda elem: elem.serialize(), favorites))
    response_body = {
        "favorites": all_favorites
    }

    return jsonify(response_body), 200

# this only runs if `$ python src/main.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
