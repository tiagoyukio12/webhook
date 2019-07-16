from app import app
from flask import request, jsonify


@app.route('/', methods=['POST'])
def post():
    #foo = request.data
    #print(foo)
    return jsonify(fulfillmentText='Olá mundo!')
