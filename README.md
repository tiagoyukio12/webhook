# webhook
Flask webhook for DialogFlow

## Requirements
- [Flask](https://flask.palletsprojects.com/en/1.1.x/)
- [ngrok](https://ngrok.com/)

## Setup
1. Install Flask and ngrok
2. `export FLASK_APP=webhook.py` (must be done every time)
3. `flask run`
4. `./ngrok http 5000`
5. Copy the forwarding address from ngrok to DialogFlow's Fulfillment Webhook url