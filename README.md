# webhook
Flask webhook for DialogFlow

## Requirements
- [Flask](https://flask.palletsprojects.com/en/1.1.x/)
- [ngrok](https://ngrok.com/)
- [Anaconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/)

## Setup
1. Install Flask, ngrok and Anaconda
2. Create an Anaconda environment\
`conda create --name web`
3. Activate Anaconda environment\
`conda activate web`
4. Install project dependencies\
`yes y | (conda install matplotlib && conda install numpy && conda install pandas && conda install statsmodels && pip install pmdarima && pip install cloudinary && pip install blynklib)`
2. Setup Flask project\
`export FLASK_APP=webhook.py`
3. `flask run`
4. Run ngrok server\
`./ngrok http 5000`
5. Copy the forwarding https address from ngrok to DialogFlow's Fulfillment Webhook url