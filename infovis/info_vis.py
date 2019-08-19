from load_house import load_house
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import operator
import calendar

import cloudinary
import cloudinary.uploader
cloudinary.config(
    cloud_name='dqmfcku4a',
    api_key='986962262222677',
    api_secret='lbTxe9ZAZsbVZJjfLJ_TgJla4aQ'
)


channels, labels = load_house.SMART('2016')


def qry_pot_channel(i_channel, start, end):
    """Runs a query for the potency [W] consumption in a channel in the specified period.

    Args:
        i_channel(int): index of the channel.
        start (str): start of the period as "YYYY-MM-DD hh:mm:ss".
        end (str): end of the period as "YYYY-MM-DD hh:mm:ss".

    Returns:
        pandas.DataFrame: as [index, time, consumption].
    """
    if i_channel < 0 or i_channel >= len(channels):
        raise Exception(
            'Channel number should be 0-{}. The value was {}'.format(len(labels) - 1, i_channel))

    # Select the desired period from channel
    ch = channels[i_channel]
    mask = (ch.t >= start) & (ch.t < end)
    ch_period = ch.loc[mask]

    return ch_period


def qry_pot_aggr(start, end, frequency):
    """Runs a query for the aggregated power [W] consumption in all channels in the specified period.

    Args:
        start (str): start of the period as "YYYY-MM-DD hh:mm:ss".
        end (str): end of the period as "YYYY-MM-DD hh:mm:ss".
        frequency (int): Frequency of sampling, in minutes.

    Returns:
        pandas.DataFrame: as [index, time, consumption].
    """
    periods = (pd.to_datetime(end) - pd.to_datetime(start)) / \
        np.timedelta64(1, 's') / (60 * frequency)
    t = pd.date_range(start, periods=periods, freq='{}min'.format(frequency))
    pot = pd.DataFrame(0, index=np.arange(periods), columns=['pot'])
    aggr_pot = pd.DataFrame([t, pot]).transpose()
    aggr_pot.columns = ['t', 'pot']
    aggr_pot.t = pd.to_datetime(aggr_pot.t)
    aggr_pot.pot = 0
    aggr_pot.index = aggr_pot.t

    for i in range(len(channels)):
        # Select the desired period from channel
        ch = channels[i]
        mask = (ch.t >= start) & (ch.t < end)
        ch_period = ch.loc[mask].copy()

        # Convert to desired sampling
        ch_period.index = ch_period.t
        upsample = ch_period.asfreq(
            freq='{}min'.format(frequency), method='ffill')
        aggr_pot['pot'] += upsample.pot

    aggr_pot = aggr_pot.reset_index(drop=True)

    return aggr_pot


def qry_cons_channel(i_channel, start, end, frequency):
    """Runs a query for the daily/weekly/monthly consumption [kWh] in a channel in the specified period.

    Args:
        i_channel (int): index of the channel.
        start (str): start of the period as "YYYY-MM-DD hh:mm:ss".
        end (str): end of the period as "YYYY-MM-DD hh:mm:ss".
        frequency (str): Period of consumption. 'D', 'W', or 'M' (daily, weekly or monthly).

    Returns:
        pandas.DataFrame: as [index, date, consumption].
    """
    if i_channel < 0 or i_channel >= len(channels):
        raise Exception(
            'Channel number should be 1-{}. The value was {}'.format(len(labels), i_channel))

    # Select the desired period from channel
    ch = channels[i_channel]
    mask = (ch.t >= start) & (ch.t < end)
    ch_period = ch.loc[mask]

    # Find mean consumption by day, week, or month
    cons = ch_period.copy()
    cons = cons.set_index('t')
    cons = cons.groupby(pd.Grouper(freq=frequency)).mean().dropna(how='all')
    cons = cons.reset_index()
    cons = pd.concat([cons.t, cons.pot], axis=1)
    cons.columns = ['t', 'energy']

    # Remove days without consumption data
    cons = cons[~cons.energy.isna()]

    # Convert to kWh
    period_hours = 24
    if frequency == 'W':
        period_hours *= 7
    if frequency == 'M':
        period_hours *= 30
    cons.energy = cons.energy * period_hours / 1e3

    return cons


def qry_cons_aggr(start, end, frequency):
    """Runs a query for the daily/weekly/monthly consumption [kWh] in all channels in the specified period.

    Args:
        start (str): start of the period as "YYYY-MM-DD hh:mm:ss".
        end (str): end of the period as "YYYY-MM-DD hh:mm:ss".
        frequency (str): Period of consumption. 'D', 'W', or 'M' (daily, weekly or monthly).

    Returns:
        pandas.DataFrame: as [index, date, consumption].
    """

    period_days = 1
    t = -1
    if frequency == 'W':
        period_days = 7
    if frequency == 'M':  # TODO: Fix monthly period
        periods = 0
        t = [pd.to_datetime(start)]
        while t[-1] + pd.offsets.MonthBegin(1) < pd.to_datetime(end):
            t.append(t[-1] + pd.offsets.MonthBegin(1))
            periods += 1
        t = pd.DatetimeIndex(t)
    else:
        periods = (pd.to_datetime(end) -
                   pd.to_datetime(start)).days / period_days
        t = pd.date_range(start, periods=periods,
                          freq='{}D'.format(period_days))

    cons = pd.DataFrame(0, index=np.arange(periods), columns=['cons'])
    aggr_cons = pd.DataFrame([t, cons]).transpose()
    aggr_cons.columns = ['t', 'energy']
    aggr_cons.t = pd.to_datetime(aggr_cons.t)
    aggr_cons.energy = 0

    for i_channel in range(len(channels)):
        # Select the desired period from channel
        ch = channels[i_channel]
        mask = (ch.t >= start) & (ch.t < end)
        ch_period = ch.loc[mask]

        # Find mean consumption by day, week, or month
        cons = ch_period.copy()
        cons = cons.set_index('t')
        cons = cons.groupby(pd.Grouper(freq=frequency)
                            ).mean().dropna(how='all')
        cons = cons.reset_index()
        cons = pd.concat([cons.t, cons.pot], axis=1)
        cons.columns = ['t', 'energy']
        cons.fillna(0)

        # Convert to kWh
        period_hours = 24 * period_days  # TODO: fix for months
        cons.energy = cons.energy * period_hours / 1e3

        aggr_cons['energy'] += cons.energy
    return aggr_cons


def qry_total_cons_all(start, end, percentage=False):
    """Runs a query for the total consumption in each channel in the specified period.

    Args:
        start (str): start of the period as "YYYY-MM-DD hh:mm:ss".
        end (str): end of the period as "YYYY-MM-DD hh:mm:ss".
        percentage (bool): if true, return percentage of total consumption of each channel.

    Returns:
        list: each element is a list of 2 elements [label (str); total consumption (float)].
    """
    total_cons = {}
    for i in range(0, len(channels)):
        # Select the desired period from channel
        ch = channels[i]
        mask = (ch.t >= start) & (ch.t < end)
        ch_period = ch.loc[mask]

        # Find mean consumption
        cons = ch_period.pot.mean()

        # Convert to kWh
        t1 = pd.to_datetime(start)
        t2 = pd.to_datetime(end)
        cons *= pd.Timedelta(t2 - t1).total_seconds() / (1e3 * 3600)

        # Add total consumption of channel i to hash map
        appliance_name = labels.iloc[i]['name']
        if appliance_name != 'mains':
            if appliance_name not in total_cons:
                total_cons[appliance_name] = cons
            else:
                total_cons[appliance_name +
                           '_1'] = total_cons.pop(appliance_name)
                total_cons[appliance_name + '_2'] = cons

    if percentage == True:
        sum = 0
        for key, value in total_cons.items():
            sum += value
        for key, value in total_cons.items():
            total_cons[key] /= sum

    sorted_tuples = sorted(
        total_cons.items(), key=operator.itemgetter(1), reverse=True)
    sorted_list = [list(elem) for elem in sorted_tuples]

    # Transpose list
    sorted_list = list(map(list, zip(*sorted_list)))

    return sorted_list


def upload_plot_cons(cons, file_name):
    """Plots a bar chart of cons, saves as png file, and uploads to Cloudinary as file_name.

    Args:
        cons (pandas.DataFrame): [index, date, consumption] DataFrame to be plotted.
        file_name (str): name of the file to be uploaded.

    Returns:
        str: url of the Cloudinary image uploaded.
    """
    # Plot query results
    fig, ax = plt.subplots()
    month_names = cons.t.dt.month.apply(
        lambda x: calendar.month_abbr[x])  # convert month numbers to names
    plt.bar(month_names, cons.energy, width=0.9, color='lightgreen')
    plt.ylabel('Consumo [kWh]')
    ax.set_yticklabels([])  # hide tick labels
    ax.tick_params(axis=u'both', which=u'both', length=0)  # hide tick marks
    plt.margins(x=0)  # remove white space

    # Add values at the top of each bar
    rects = ax.patches
    bar_labels = ["{:5.1f}".format(cons.iloc[i].energy)
                  for i in range(len(rects))]
    for rect, label in zip(rects, bar_labels):
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() * 0.43, height * 0.93, label,
                ha='center', va='bottom', weight='bold')
    #fig.set_size_inches(12, 6)
    plt.savefig('./app/' + file_name + '.png')
    cloudinary.uploader.upload(
        './app/' + file_name + '.png', public_id=file_name)

    return cloudinary.utils.cloudinary_url(file_name)[0]
