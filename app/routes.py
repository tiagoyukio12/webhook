import json

from datetime import date
from flask import request, jsonify, send_file
from app import app
from infovis import info_vis
from forecast import forecast


@app.route('/', methods=['POST'])
def post():
    data = json.loads(request.data)

    intent = data['queryResult']['intent']['displayName']
    if intent == 'Consumo':
        # Get start and end dates
        # TODO: get frequency (D, W, M) depending on period length
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
        # TODO: format date to "22/04/2019 or April, 22, 2019, etc"
        fulfillment_text = 'Você consumiu {} kWh de {} a {}'.format(
            round(cons.energy.sum(), 2), start_date, end_date)
        response['fulfillmentText'] = fulfillment_text
        response['fulfillmentMessages'][0]['text']['text'][0] = fulfillment_text
        response['fulfillmentMessages'][2]['simpleResponses']['simpleResponses'][0]['textToSpeech'] = fulfillment_text
        response['fulfillmentMessages'][5]['text']['text'][0] = fulfillment_text

        # Create media file url
        response['fulfillmentMessages'][1]['image']['imageUri'] = url
        # response['fulfillmentMessages'][1]['image']['imageUri'] = url
        response['fulfillmentMessages'][3]['basicCard']['image']['imageUri'] = url
        response['fulfillmentMessages'][7]['payload']['line']['template']['thumbnailImageUrl'] = url

        return jsonify(response)

    if intent == 'Predicao':
        today = date.today()
        start_date = format_date(today.strftime("%Y-%m-%d"))
        print(start_date)
        print('asdad')
        end_date = format_date(data['queryResult']['parameters']['date-time']['endDate'])

        cons = info_vis.qry_cons_aggr('2016-01-01', start_date, 'M')
        # TODO: predicted = forecast.ARIMA(...)

        fulfillment_text = 'Você consumirá {} kWh até {}'.format(
            round(cons.energy.sum(), 2), end_date)

        plot_name = 'cons' + data['responseId']

        fulfillment_text = 'Você consumirá {} kWh de {} a {}'.format(
            round(cons.energy.sum(), 2), start_date, end_date)
        # TODO: url = info_vis.upload_plot_cons(cons, plot_name)

        # Load json response
        file_handler = open('./app/response.json', 'r')
        response = json.loads(file_handler.read())

        # Modify json response
        response['fulfillmentText'] = fulfillment_text
        response['fulfillmentMessages'][0]['text']['text'][0] = fulfillment_text
        response['fulfillmentMessages'][2]['simpleResponses']['simpleResponses'][0]['textToSpeech'] = fulfillment_text
        response['fulfillmentMessages'][5]['text']['text'][0] = fulfillment_text
        #response['fulfillmentMessages'][1]['image']['imageUri'] = url
        #response['fulfillmentMessages'][3]['basicCard']['image']['imageUri'] = url
        #response['fulfillmentMessages'][7]['payload']['line']['template']['thumbnailImageUrl'] = url

        return jsonify(response)

    if intent == 'Sugestoes':
        return -1


def format_date(date):
    date = date[:3] + '6' + date[4:]  # TODO: remove me
    return date[:10] + ' ' + date[11:19]


@app.route('/media', methods=['GET'])
def get_image():
    file = request.args.get('file')
    return send_file(file, mimetype='image/gif')
