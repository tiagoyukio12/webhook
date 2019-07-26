import os
import pandas as pd


def REDD(i_house):
    """Loads data from a REDD dataset house. The 'low_freq' directory must be in the root of the project.
    
    Args:
        i_house (int): index of the house.
    
    Returns:
        (list, DataFrame): tuple of a list of each channAel consumption data,
        and a DataFrame of the labels identifying the appliance of each channel.
    """
    path = 'low_freq/house_{}/'.format(i_house)
    num_channels = len([name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))]) - 1

    # Load consumption data
    channels = []
    for i in range(num_channels):
        ch = pd.read_csv(path + 'channel_{}.dat'.format(i + 1), delimiter=' ', names=['t', 'pot'])
        ch.t = pd.to_datetime(ch.t, unit='s')
        channels.append(ch)

    # Load labels
    labels = pd.read_csv(path + 'labels.dat', delimiter=' ', names=['i', 'name'])
    
    return channels, labels


def SMART(year):
    """Loads data from a SMART dataset house. The 'HomeA' directory must be in the root of the project.
    
    Args:
        year (str): desired year to be loaded.
    
    Returns:
        (list, DataFrame): tuple of a list of each channel consumption data,
        and a DataFrame of the labels identifying the appliance of each channel.
    """
    path = 'HomeA/{}/'.format(year)
    
    labels = pd.DataFrame(columns=['name'])
    channels = list()
    # Load data for each meter (2-4)
    for i in range(2, 5):
        meter_data = pd.read_csv(path + 'HomeA-meter{}_{}.csv'.format(i, year), delimiter=',')
        label = pd.DataFrame(list(meter_data)[3:], columns=['name'])
        labels = labels.append(label, ignore_index=True)
        t = pd.to_datetime(meter_data.iloc[:, 0]).rename('t')
        t = pd.to_datetime(t, unit='s')
        
        # Add each channel as a DataFrame with columns ['t', 'pot']
        for i in range(3, len(meter_data.columns)):
            channel = pd.DataFrame(t)
            channel['pot'] = meter_data.iloc[:,i]
            channel.loc[:,'pot'] *= 1e3  # Convert from kW to W
            channels.append(channel)
    
    labels['name'] = labels['name'].astype(str).str[:-5]  # Remove ' [kW]' from string
    return channels, labels
