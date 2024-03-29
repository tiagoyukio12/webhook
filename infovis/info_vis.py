import calendar
import operator

import cloudinary
import cloudinary.uploader
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from load_house import load_house

cloudinary.config(
    cloud_name='dqmfcku4a',
    api_key='986962262222677',
    api_secret='lbTxe9ZAZsbVZJjfLJ_TgJla4aQ'
)

CHANNELS, LABELS = load_house.SMART('2016')


def qry_pot_channel(i_channel, start, end):
    """Runs a query for the potency [W] consumption in a channel in the specified period.

    Args:
        i_channel(int): index of the channel.
        start (str): start of the period as "YYYY-MM-DD hh:mm:ss".
        end (str): end of the period as "YYYY-MM-DD hh:mm:ss".

    Returns:
        pandas.DataFrame: as [index, 't', 'pot'].
    """
    if i_channel < 0 or i_channel >= len(CHANNELS):
        raise Exception(
            'Channel number should be 0-{}. The value was {}'.format(
                len(LABELS) - 1, i_channel))

    # Select the desired period from channel
    channel = CHANNELS[i_channel]
    mask = (channel.t >= start) & (channel.t < end)
    ch_period = channel.loc[mask]

    return ch_period


def qry_pot_aggr(start, end, frequency):
    """Runs a query for the aggregated power [W] consumption in all channels in the specified period.

    Args:
        start (str): start of the period as "YYYY-MM-DD hh:mm:ss".
        end (str): end of the period as "YYYY-MM-DD hh:mm:ss".
        frequency (int): Frequency of sampling, in minutes.

    Returns:
        pandas.DataFrame: as [index, 't', 'pot'].
    """
    periods = (pd.to_datetime(end) - pd.to_datetime(start)) / np.timedelta64(1, 's') / (60 * frequency)
    t = pd.date_range(start, periods=periods, freq='{}min'.format(frequency))
    pot = pd.DataFrame(0, index=np.arange(periods), columns=['pot'])
    aggr_pot = pd.DataFrame([t, pot]).transpose()
    aggr_pot.columns = ['t', 'pot']
    aggr_pot.t = pd.to_datetime(aggr_pot.t)
    aggr_pot.pot = 0
    aggr_pot.index = aggr_pot.t

    for i, channel in enumerate(CHANNELS):
        # Select the desired period from channel
        mask = (channel.t >= start) & (channel.t < end)
        ch_period = channel.loc[mask].copy()

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
        pandas.DataFrame: as [index, 't', 'energy'].
    """
    if i_channel < 0 or i_channel >= len(CHANNELS):
        raise Exception(
            'Channel number should be 1-{}. The value was {}'.format(len(LABELS), i_channel))

    # Select the desired period from channel
    channel = CHANNELS[i_channel]
    mask = (channel.t >= start) & (channel.t < end)
    ch_period = channel.loc[mask]

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
        pandas.DataFrame: as [index, 't', 'energy'].
    """

    period_days = 1

    if frequency == 'M':
        periods = 0
        t = [pd.to_datetime(start)]
        while t[-1] + pd.offsets.MonthBegin(1) < pd.to_datetime(end):
            t.append(t[-1] + pd.offsets.MonthBegin(1))
            periods += 1
        t.append(pd.to_datetime(end))
        periods += 1
        t = pd.DatetimeIndex(t)
    elif frequency == 'W':
        period_days = 7
        periods = (pd.to_datetime(end) -
                   pd.to_datetime(start)).days / period_days
        t = pd.date_range(start, periods=periods, freq='W')
    else:
        periods = (pd.to_datetime(end) -
                   pd.to_datetime(start)).days / period_days + 1
        t = pd.date_range(start, periods=periods,
                          freq='D')

    cons = pd.DataFrame(0, index=np.arange(periods), columns=['cons'])
    aggr_cons = pd.DataFrame([t, cons]).transpose()
    aggr_cons.columns = ['t', 'energy']
    aggr_cons.t = pd.to_datetime(aggr_cons.t)
    aggr_cons.energy = 0

    for i_channel in range(len(CHANNELS)):
        # Select the desired period from channel
        ch = CHANNELS[i_channel]
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
        if frequency == 'M':
            for i in range(aggr_cons.shape[0] - 1):
                period_hours = (
                                       aggr_cons.t.iloc[i + 1] - aggr_cons.t.iloc[i]) / np.timedelta64(1, 'h')
                cons.at['energy', i] = aggr_cons.energy.iloc[i] * period_hours / 1e3
        else:
            period_hours = 24 * period_days
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
    for i, channel in enumerate(CHANNELS):
        # Select the desired period from channel
        mask = (channel.t >= start) & (channel.t < end)
        ch_period = channel.loc[mask]

        # Find mean consumption
        cons = ch_period.pot.mean()

        # Convert to kWh
        t1 = pd.to_datetime(start)
        t2 = pd.to_datetime(end)
        cons *= pd.Timedelta(t2 - t1).total_seconds() / (1e3 * 3600)

        # Add total consumption of channel i to hash map
        appliance_name = LABELS.iloc[i]['name']
        if appliance_name != 'mains':
            if appliance_name not in total_cons:
                total_cons[appliance_name] = cons
            else:
                total_cons[appliance_name +
                           '_1'] = total_cons.pop(appliance_name)
                total_cons[appliance_name + '_2'] = cons

    if percentage:
        sum_cons = 0
        for key, value in total_cons.items():
            sum_cons += value
        for key, value in total_cons.items():
            total_cons[key] /= sum_cons

    sorted_tuples = sorted(
        total_cons.items(), key=operator.itemgetter(1), reverse=True)
    sorted_list = [list(elem) for elem in sorted_tuples]

    # Transpose list
    sorted_list = list(map(list, zip(*sorted_list)))

    return sorted_list


def upload_plot_cons(cons, frequency, file_name):
    """Plots a bar chart of cons, saves as png file, and uploads to Cloudinary as file_name.

    Args:
        cons (pandas.DataFrame): [index, date, consumption] DataFrame to be plotted.
        frequency (str): Period of consumption. 'D', 'W', or 'M' (daily, weekly or monthly).
        file_name (str): name of the file to be uploaded.

    Returns:
        str: url of the Cloudinary image uploaded.
    """
    # Plot query results
    # TODO: fix daily consumption query plot
    fig, ax = plt.subplots()
    if frequency == 'M':
        month_names = cons.t.dt.month.apply(
            lambda x: calendar.month_abbr[x])  # convert month numbers to names
        plt.bar(month_names, cons.energy, width=0.9, color='lightgreen')
    else:
        plt.bar(cons.t, cons.energy, width=0.9, color='lightgreen')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        plt.xticks(rotation='vertical')
    plt.ylabel('Consumo [kWh]')
    ax.set_yticklabels([])  # hide tick labels
    ax.tick_params(axis=u'both', which=u'both', length=0)  # hide tick marks
    plt.margins(x=0)  # remove white space

    # Add values at the top of each bar
    rects = ax.patches
    bar_labels = ["{:5.0f}".format(cons.iloc[i].energy)
                  for i in range(len(rects))]
    for rect, label in zip(rects, bar_labels):
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() * 0.33, height - 1.5, label,
                ha='center', va='bottom', weight='bold')
    fig.set_size_inches(12, 6)
    plt.savefig('./app/' + file_name + '.png')
    cloudinary.uploader.upload(
        './app/' + file_name + '.png', public_id=file_name)

    return cloudinary.utils.cloudinary_url(file_name, secure=True)[0]


def upload_plot_ind_cons(sorted_cons, file_name):
    """Plots a pie chart of cons, saves as png file, and uploads to Cloudinary as file_name.

    Args:
        sorted_cons (list): each element is a list of 2 elements [label (str); total consumption (float)].
        file_name (str): name of the file to be uploaded.

    Returns:
        str: url of the Cloudinary image uploaded.
    """
    max_channels = 8
    sum_others = 0
    for i in range(max_channels, len(sorted_cons[1])):
        sum_others += sorted_cons[1][i]

    sorted_cons[0] = sorted_cons[0][:max_channels] + ['Outros']
    sorted_cons[1] = sorted_cons[1][:max_channels] + [sum_others]

    cmap = plt.cm.Accent
    colors = cmap(np.linspace(0., 1., len(sorted_cons[0])))

    fig1, ax1 = plt.subplots()

    explode = [0.05] * (max_channels + 1)

    def autopct_format(values):
        def my_format(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return '{v:d}'.format(v=val)

        return my_format

    ax1.pie(sorted_cons[:][1], labels=sorted_cons[0], startangle=90,
            counterclock=False, autopct=autopct_format(sorted_cons[:][1]),
            colors=colors, pctdistance=0.85, explode=explode)

    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    ax1.axis('equal')
    plt.tight_layout()
    fig.set_size_inches(12, 6)
    plt.savefig('./app/' + file_name + '.png')
    cloudinary.uploader.upload(
        './app/' + file_name + '.png', public_id=file_name)

    return cloudinary.utils.cloudinary_url(file_name, secure=True)[0]
