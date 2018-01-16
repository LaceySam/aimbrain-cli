import base64
import hashlib
import hmac
import json
import urlparse

import requests

from aimbrain.commands.base import BaseCommand


V1_FACE_AUTH_ENDPOINT = '/v1/face/auth'
V1_FACE_COMPARE_ENDPOINT = '/v1/face/compare'
V1_FACE_ENROLL_ENDPOINT = '/v1/face/enroll'
V1_SESSIONS_ENDPOINT = '/v1/sessions'

V1_VOICE_AUTH_ENDPOINT = '/v1/voice/auth'
V1_VOICE_ENROLL_ENDPOINT = '/v1/voice/enroll'
V1_VOICE_TOKEN_ENDPOINT = '/v1/voice/token'


class AbstractRequestGenerator(BaseCommand):
    def __init__(self, options, *args, **kwargs):
        super(AbstractRequestGenerator, self).__init__(options, args, kwargs)

        self.user_id = options.get('--user-id')
        self.secret = options.get('--secret')
        self.api_key = options.get('--api-key')

        if options.get('--dev'):
            self.base_url = 'dev.aimbrain.com'
        else:
            self.base_url = 'aimbrain.com'

    def get_hmac_sig(self, method, endpoint, body):
        message = '%s\n%s\n%s' % (method.upper(), endpoint.lower(), body)

        return base64.b64encode(hmac.new(
            self.secret.encode('utf-8'),
            bytes(message).encode('utf-8'),
            digestmod=hashlib.sha256,
        ).digest())

    def get_url(self, endpoint):
        return urlparse.urlunparse((
            'https',
            self.base_url,
            endpoint,
            '',
            '',
            '',
        ))

    def get_session(self):
        payload = json.dumps({
            'userId': self.user_id,
            'device': 'Phone',
            'system': 'Linux'
        })

        session_url = self.get_url(V1_SESSIONS_ENDPOINT)
        headers = self.get_aimbrain_headers('POST', V1_SESSIONS_ENDPOINT, payload)
        resp = requests.post(session_url, payload, headers=headers)

        return resp.json().get('session')

    def get_aimbrain_headers(self, method, endpoint, body):
        return {
            'X-Aimbrain-Apikey': self.api_key,
            'X-Aimbrain-Signature': self.get_hmac_sig(method, endpoint, body),
        }

    def encode_biometric(self, biometric_path):
        encoded = None
        with open(biometric_path, 'rb') as f:
            image = f.read()
            encoded = base64.b64encode(image)

        return encoded

    def do_request(self, endpoint, body):
        payload = json.dumps(body)
        headers = self.get_aimbrain_headers('POST', endpoint, payload)
        request_url = self.get_url(endpoint)

        resp = requests.post(request_url, payload, headers=headers)

        return resp.json()


class Auth(AbstractRequestGenerator):

    def __init__(self, options, *args, **kwargs):
        super(Auth, self).__init__(options, args, kwargs)

        self.auth_type = 'face' if options.get('face') else 'voice'
        self.biometrics = options.get('<biometrics>')

    def run(self):
        body = {'session': self.get_session()}
        endpoint = ''
        if self.auth_type == 'face':
            endpoint = V1_FACE_AUTH_ENDPOINT
            body['faces'] = []
            for face in self.biometrics:
                body['faces'].append(self.encode_biometric(face))

        payload = self.do_request(endpoint, body)
        print payload