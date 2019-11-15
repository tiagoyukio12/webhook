import csv
import calendar
import datetime
import operator
import os

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib as mpl
import numpy as np
import pandas as pd

import cloudinary
import cloudinary.uploader
cloudinary.config(
    cloud_name='dqmfcku4a',
    api_key='986962262222677',
    api_secret='lbTxe9ZAZsbVZJjfLJ_TgJla4aQ'
)

from load_house import load_house

from io import StringIO
from matplotlib import rcParams
from pandas.plotting import register_matplotlib_converters
from pmdarima.arima import auto_arima
from statsmodels.tsa.arima_model import ARMA
from statsmodels.tsa.arima_model import ARIMA


# Don't cut xlabel when saving .fig
rcParams.update({'figure.autolayout': True})

# Convert datetime for matplotlib
register_matplotlib_converters()

# Create directory for matplotlib figures
if not os.path.exists('plot/ARIMA'):
    os.makedirs('plot/ARIMA')


def qry_ARIMA(cons, start_date, end_date, pdq):
    """Runs a query for the forecast consumption using an ARIMA model.

    Args:
        cons (pandas.DataFrame): [index, date, consumption] DataFrame of past consumption.
        start_date (str): YYYY-MM-DD date of the forecast period's start.
        end_date (str): YYYY-MM-DD date of the forecast period's end.
        pdq (iterable): order of the model parameters.

    Returns:
        pandas.DataFrame: forecasted consumption as ['t', 'energy'].
    """
    cons.energy.fillna(cons.energy.mean(), inplace=True)  # ARIMA doesn't work with NaN values
    model = ARIMA(cons.energy, pdq)
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    days_predicted = int((end_date - start_date) / np.timedelta64(1,'D'))
    model_fit = model.fit(disp=0)
    predict_cons = model_fit.forecast(days_predicted)[0]
    
    date_list = [start_date + datetime.timedelta(days=x) for x in range(days_predicted)]
    result = pd.DataFrame([date_list, predict_cons]).transpose()
    result.columns = ['t', 'energy']

    return result

    
def upload_plot_cons(cons, predict_cons, file_name):
    """Plots a bar chart, saves as png file, and uploads to Cloudinary as file_name.

    Args:
        cons (pandas.DataFrame): [index, date, consumption] DataFrame to be plotted.
        predict_cons (pandas.DataFrame): [index, date, consumption] DataFrame to be plotted.
        file_name (str): name of the file to be uploaded.

    Returns:
        str: url of the Cloudinary image uploaded.
    """
    # Plot query results
    fig, ax = plt.subplots()
    plt.bar(cons.t, cons.energy, width=0.9, color='lightgreen')
    plt.bar(predict_cons.t, predict_cons.energy, width=0.9, color='lightblue')
    plt.ylabel('Consumo [kWh]')
    ax.set_yticklabels([])  # hide tick labels
    ax.tick_params(axis=u'both', which=u'both', length=0)  # hide tick marks
    plt.margins(x=0)  # remove white space
    plt.xticks(rotation='vertical')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

    plt.savefig('./app/' + file_name + '.png')
    cloudinary.uploader.upload(
        './app/' + file_name + '.png', public_id=file_name)

    return cloudinary.utils.cloudinary_url(file_name, secure=True)[0]