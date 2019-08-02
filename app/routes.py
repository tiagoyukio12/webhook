import json
import calendar

import matplotlib.pyplot as plt
from app.infovis import info_vis

from app import app
from flask import request, jsonify, send_file


@app.route('/', methods=['POST'])
def post():
    data = json.loads(request.data)
    
    if data['queryResult']['parameters']['date'] != '':
        # Parameter received is a specific date
        start_date = format_date(data['queryResult']['parameters']['date'])
        end_date = start_date + 1  # TODO: increment string by 1 day
    else:
        # Parameter received is a period
        start_date = format_date(data['queryResult']['parameters']['date-period']['startDate'])
        print(start_date)
        end_date = format_date(data['queryResult']['parameters']['date-period']['endDate'])

    cons = info_vis.qry_cons_aggr(start_date, end_date, 'M')

    # Plot query results
    fig, ax = plt.subplots()
    month_names = cons.t.dt.month.apply(lambda x: calendar.month_abbr[x])  # convert month numbers to names
    plt.bar(month_names, cons.energy, width=0.9, color='lightgreen')
    plt.ylabel('Consumo [kWh]')
    ax.set_yticklabels([])  # hide tick labels
    ax.tick_params(axis=u'both', which=u'both',length=0)  # hide tick marks
    plt.margins(x=0)  # remove white space

    # Add values at the top of each bar
    rects = ax.patches
    bar_labels = ["{:5.0f}".format(cons.iloc[i].energy) for i in range(len(rects))]
    for rect, label in zip(rects, bar_labels):
        height = rect.get_height()
        ax.text(rect.get_x() - 0.05 + rect.get_width()/2, height - 30, label,
                ha='center', va='bottom', weight = 'bold')
    fig.set_size_inches(12, 6)
    plt.savefig('./app/plot' + data['responseId'] + '.png')

    # Load json response
    file_handler = open('./app/response.json', 'r')
    response = json.loads(file_handler.read())
    fulfillmentText = 'Você consumiu {} kWh de {} a {}'.format(cons.energy.iloc[0], start_date, end_date)
    response['fulfillmentText'] = fulfillmentText
    response['fulfillmentMessages'][2]['text']['text'][0] = fulfillmentText

    # Create media file url
    url = request.url_root + 'media?file=' + 'plot' + data['responseId'] + '.png'
    response['fulfillmentMessages'][0]['image']['imageUri'] = url
    response['fulfillmentMessages'][1]['image']['imageUri'] = url  # FIXME: image from ngrok doesn't load in facebook

    return jsonify(response)

def format_date(date):
    return date[:10] + ' ' + date[11:19]

@app.route('/media', methods=['GET'])
def get_image():
    file = request.args.get('file')
    return send_file(file, mimetype='image/gif')