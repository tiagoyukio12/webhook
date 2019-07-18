import json

from app import app
from flask import request, jsonify


@app.route('/', methods=['POST'])
def post():
    data = json.loads(request.data)
    date = data['queryResult']['parameters']['date']

    cons = 8

    #return jsonify(fulfillmentText='Você consumiu {} kWh em {}'.format(cons, date))
    file_handler = open('./app/response.json', 'r')
    response = json.loads(file_handler.read())
    return jsonify(response)