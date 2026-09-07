import jwt

LOGOUT_EVENT = 'http://schemas.openid.net/event/backchannel-logout'


def validate_logout_token(token, key, issuer, audience):
    claims = jwt.decode(
        token, key, algorithms=['RS256'], issuer=issuer, audience=audience,
        options={'require': ['iss', 'aud', 'iat', 'exp', 'jti', 'sid', 'events']},
    )
    from time import time
    if time() - claims['iat'] > 300:
        raise ValueError('Logout token too old')
    if 'nonce' in claims or not isinstance(claims['sid'], str) or not claims['sid']:
        raise ValueError('Invalid logout token')
    if not isinstance(claims['jti'], str) or not claims['jti']:
        raise ValueError('Invalid logout token ID')
    events = claims['events']
    if not isinstance(events, dict) or events.get(LOGOUT_EVENT) != {}:
        raise ValueError('Missing logout event')
    return claims
