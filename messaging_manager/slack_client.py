import requests

from .constants import ServiceURL


class SlackClient:
    def send_slack(self, channel, message, colour='#666666'):
        try:
            response = requests.post(
                url=f'{ServiceURL.SERVICE_URL}{channel}',
                json={
                    'username': 'Noe',
                    'icon_emoji': ':rocket:',
                    'attachments': [
                        {
                            'fallback': message,
                            'color': colour,
                            'fields': [
                                {
                                    'value': message,
                                    'short': False,
                                }
                            ],
                        }
                    ],
                },
                timeout=30,
            )
            response.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            print(
                'Warning: failed to send message to Slack, connection issue or timeout'
            )
        except requests.exceptions.HTTPError as e:
            print(
                f'Warning: failed to send message to Slack, error response to HTTP request ({e})'
            )
