from flask import request, jsonify, send_file
from app import app
from infovis import info_vis
import json


@app.route('/', methods=['POST'])
def post():
    data = json.loads(request.data)

    intent = data['queryResult']['intent']['displayName']
    if intent == 'Consumo':
        # Get start and end dates
        # TODO: get frequency (monthly, weekly or daily) depending on period length
        if data['queryResult']['parameters']['date'] != '':
            # Parameter received is a specific date
            start_date = format_date(data['queryResult']['parameters']['date'])
            end_date = start_date + 1  # TODO: increment string by 1 day
        else:
            # Parameter received is a period
            start_date = format_date(
                data['queryResult']['parameters']['date-period']['startDate'])
            end_date = format_date(
                data['queryResult']['parameters']['date-period']['endDate'])

        cons = info_vis.qry_cons_aggr(start_date, end_date, 'M')
        plot_name = 'cons' + data['responseId']
        url = info_vis.upload_plot_cons(cons, plot_name)

        # Load json response
        file_handler = open('./app/response.json', 'r')
        response = json.loads(file_handler.read())
        fulfillmentText = 'Você consumiu {} kWh de {} a {}'.format(
            round(cons.energy.sum(), 2), start_date, end_date)
        response['fulfillmentText'] = fulfillmentText
        response['fulfillmentMessages'][2]['text']['text'][0] = fulfillmentText
        response['fulfillmentMessages'][3]['simpleResponses']['simpleResponses'][0]['textToSpeech'] = fulfillmentText
        response['fulfillmentMessages'][7]['text']['text'][0] = fulfillmentText

        # Create media file url
        response['fulfillmentMessages'][0]['image']['imageUri'] = url
        response['fulfillmentMessages'][1]['image']['imageUri'] = url
        response['fulfillmentMessages'][4]['basicCard']['image']['imageUri'] = url
        # TODO: try ngrok http link for Line
        response['fulfillmentMessages'][6]['image']['imageUri'] = url

        return jsonify(response)

    elif intent == 'Predicao':
        return -1
    elif intent == 'Recomendacao':
        return -1


def format_date(date):
    date = date[:3] + '6' + date[4:]  # TODO: remove me
    return date[:10] + ' ' + date[11:19]


@app.route('/media', methods=['GET'])
def get_image():
    file = request.args.get('file')
    return send_file(file, mimetype='image/gif')
