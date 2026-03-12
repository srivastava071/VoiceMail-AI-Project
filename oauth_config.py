from authlib.integrations.flask_client import OAuth

def init_oauth(app):
    oauth = OAuth(app)

    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile https://www.googleapis.com/auth/gmail.modify',
            
        }
    )

    return google