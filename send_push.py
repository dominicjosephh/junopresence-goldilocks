import requests
import json

EXPO_PUSH_TOKEN = 'ExponentPushToken[YOUR_DEVICE_TOKEN_HERE]'  # 👈 Replace with your real token

def send_push_notification(title, body):
    message = {
        'to': EXPO_PUSH_TOKEN,
        'sound': 'default',
        'title': title,
        'body': body,
        'data': {'extra': 'Juno push test'}
    }

    response = requests.post(
        'https://exp.host/--/api/v2/push/send',
        data=json.dumps(message),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    )

    print('Push Response:', response.status_code, response.text)

if __name__ == "__main__":
    send_push_notification("Morning Ritual 🌞", "Good morning, Dom. I’m here and ready to start the day with you.")
