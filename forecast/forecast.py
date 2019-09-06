import csv
import datetime
import operator
import os

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd

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


def qry_ARIMA(days_predicted, pdq):
    """Runs a query for the forecast consumption using an ARIMA model.

    Args:
        days_predicted (int): number of days to forecast.
        pdq (iterable): order of the model parameters.

    Returns:
        str: csv of the query as [index, date, daily forecasted consumption].
    """
    model = ARIMA(test.energy, pdq)
    model_fit = model.fit(disp=0)
    predicted = model_fit.forecast(days_predicted)

    # Add daily consumption of current day
    predict_cons = np.insert(predicted[0], 0, test.energy.iloc[-1])

    # Convert to pandas.DataFrame
    result = pd.DataFrame(np.transpose(
        [np.insert(validation.t.values, 0, test.t.iloc[-1]), predict_cons]))
    result.columns = ['t', 'energy']

    return result.to_csv()