import json
from datetime import date, datetime, timedelta

import blynklib
import serial
from flask import request, jsonify

from app import app
from forecast import forecast
from infovis import info_vis

# initialize blynk
BLYNK_AUTH = '4sYLFkG0xPGFOua7JKBTkpNSbTzcyATe'
blynk = blynklib.Blynk(BLYNK_AUTH)
blynk.run()

# Arduino
ser = serial.Serial()
try:
    ser = serial.Serial('/dev/ttyUSB0', 9600)
except Exception as error:
    print(error)


@app.route('/', methods=['POST'])
def post():
    data = json.loads(request.data)

    intent = data['queryResult']['intent']['displayName']
    if intent == 'Consumo':
        # Get start and end dates
        if data['queryResult']['parameters']['date'] != '':
            # Parameter received is a specific date
            start_date = format_date(data['queryResult']['parameters']['date'])
            end_date = (datetime.strptime(start_date[:10], '%Y-%m-%d') + timedelta(days=1)).strftime(
                "%Y-%m-%d %H:%M:%S")
        else:
            # Parameter received is a period
            start_date = format_date(data['queryResult']['parameters']['date-period']['startDate'])
            end_date = format_date(data['queryResult']['parameters']['date-period']['endDate'])

        response = qry_cons(start_date, end_date, data['responseId'])
        return jsonify(response)

    if intent == 'Consumo Individual':
        # Get start and end dates
        if data['queryResult']['parameters']['date-time'] != '':
            # TODO: se query for "quanto consumi hoje?"
            # Parameter received is a period
            start_date = format_date(data['queryResult']['parameters']['date-time']['startDate'])
            end_date = format_date(data['queryResult']['parameters']['date-time']['endDate'])
        else:
            # No date-time parameter received. Use month consumption
            start_date = format_date(datetime.today().replace(day=1).strftime('%Y-%m-%d'))
            end_date = format_date(datetime.today().strftime('%Y-%m-%d'))

        response = qry_ind_cons(start_date, end_date, data['responseId'])
        return jsonify(response)

    if intent == 'Predicao':
        # Get start and end dates
        start_date = format_date(date.today().strftime("%Y-%m-%d"))
        end_date = format_date(data['queryResult']['parameters']['date-time']['endDate'])

        response = qry_forecast(start_date, end_date, data['responseId'])
        return jsonify(response)

    if intent == 'Sugestoes':
        start_date = format_date((datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d"))
        end_date = format_date(datetime.now().strftime("%Y-%m-%d"))

        response = qry_suggestion(start_date, end_date, data['responseId'])
        return jsonify(response)


def qry_cons(start_date, end_date, response_id):
    date_format = '%Y-%m-%d %H:%M:%S'
    period = datetime.strptime(end_date, date_format) - datetime.strptime(start_date, date_format)
    frequency = 'D'
    if period > timedelta(days=90):
        frequency = 'M'
    elif period > timedelta(weeks=5):
        frequency = 'W'

    cons = info_vis.qry_cons_aggr(start_date, end_date, frequency)

    # TODO: beautify date to "22/04/2019 or April, 22, 2019"
    txt = 'Você consumiu {} kWh de {} a {}'.format(
        round(cons.energy.sum(), 2), start_date, end_date)
    plot_name = 'cons' + response_id
    img_url = info_vis.upload_plot_cons(cons, frequency, plot_name)

    # Send data to Blynk
    update_blynk(0, cons)

    # Send to Arduino
    if ser.is_open:
        ser.write(b'a')

    # Load json response
    response = jsonify_response(txt, img_url)

    return response


def qry_ind_cons(start_date, end_date, response_id):
    sorted_cons = info_vis.qry_total_cons_all(start_date, end_date,
                                              percentage=False)

    txt = 'O aparelho que mais consumiu foi {}, gastando {} kWh.'.format(
        sorted_cons[0][0], round(sorted_cons[1][0], 2))
    plot_name = 'ind_cons' + response_id
    img_url = info_vis.upload_plot_ind_cons(sorted_cons, plot_name)

    # Send data to Blynk
    update_blynk(1, sorted_cons)

    # Send to Arduino
    if ser.is_open:
        ser.write(b's')

    # Load json response
    response = jsonify_response(txt, img_url)
    return response


def qry_forecast(start_date, end_date, response_id):
    cons = info_vis.qry_cons_aggr('2016-08-01', start_date, 'D')

    # TODO: use non-linear model instead of ARIMA
    predicted = forecast.qry_ARIMA(cons, start_date, end_date, (4, 0, 2))

    txt = 'Você consumirá {} kWh de {} a {}'.format(
        round(predicted.energy.sum(), 2), start_date, end_date)
    plot_name = 'cons' + response_id
    img_url = forecast.upload_plot_cons(cons, predicted, plot_name)

    # Send data to Blynk
    update_blynk(2, [cons, predicted])

    # Load json response
    response = jsonify_response(txt, img_url)
    return response


def qry_suggestion(start_date, end_date, response_id):
    sorted_cons = info_vis.qry_total_cons_all(start_date, end_date,
                                              percentage=False)
    villain = sorted_cons[0][0]
    txt = '{} está consumindo acima do normal. Que tal comprar um novo?'.format(villain)
    if villain == 'FurnaceHRV':
        txt = 'O sistema de aquecimento foi o que mais consumiu este mês. Você deve trocar os filtros a cada 2 meses.'
    elif villain == 'OfficeLights':
        txt = 'Não acenda luzes durante o dia. Que tal abrir as janelas?'
    elif villain == 'Refrigerator':
        txt = 'A geladeira foi o aparelho que mais consumiu este mês. Lembre-se de descongelar regularmente,'
    elif villain == 'Dryer':
        txt = 'A secadora foi o aparelho que mais consumiu este mês. Limpe o duto de exaustão regularmente.'

    plot_name = 'ind_cons' + response_id
    img_url = info_vis.upload_plot_ind_cons(sorted_cons, plot_name)

    # Load json response
    response = jsonify_response(txt, img_url)
    return response


def jsonify_response(txt, img_url):
    """Updates DialogFlow response.json text and image url fields.

    Args:
        txt (str): Fulfillment message.
        img_url (str): image URL.

    Returns:
        dictionary: updated response.json as a Python data structure.
    """
    file_handler = open('./app/response.json', 'r')
    response = json.loads(file_handler.read())

    # Modify text
    response['fulfillmentText'] = txt
    response['fulfillmentMessages'][0]['text']['text'][0] = txt
    response['fulfillmentMessages'][2]['simpleResponses']['simpleResponses'][0]['textToSpeech'] = txt
    response['fulfillmentMessages'][5]['text']['text'][0] = txt

    # Create media file url
    response['fulfillmentMessages'][1]['image']['imageUri'] = img_url
    response['fulfillmentMessages'][3]['basicCard']['image']['imageUri'] = img_url
    response['fulfillmentMessages'][7]['payload']['line']['template']['thumbnailImageUrl'] = img_url
    return response


def format_date(date):
    """Formats date to Pandas readable format.

    Args:
        date (str): unformatted date.

    Returns:
        str: YYYY-MM-DD date.
    """
    formatted_date = date[:2] + '16' + date[4:]  # Use 2016 Smart Data
    return formatted_date[:10] + ' ' + formatted_date[11:19]


def update_blynk(tv_status, data):
    """Updates blynk V11 pin value to tv_status.

    Args:
        tv_status (int): 0 for consumption, 1 for individual consumption, and
            2 for forecast.
        data (list, pandas.DataFrame): result consumption from query
    """
    blynk.virtual_write(11, tv_status)

    cons_json = ""
    if tv_status == 0:
        cons_json = data.to_json()
    elif tv_status == 1:
        cons_json = json.dumps(data)
    elif tv_status == 2:
        cons_json = data[0].to_json() + data[1].to_json()

    blynk.virtual_write(12, cons_json)
