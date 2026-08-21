import sys
import os

# Root directory setup
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.chdir(root_dir)

from app import app

class VercelWSGIHandler:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Fix PATH_INFO if Vercel rewrote it to the handler path
        path_info = environ.get('PATH_INFO', '')
        matched = environ.get('HTTP_X_MATCHED_PATH')
        
        if matched:
            matched_path = matched.split('?', 1)[0]
            if not matched_path.startswith('/api/index'):
                environ['PATH_INFO'] = matched_path
        elif path_info.startswith('/api/index.py'):
            environ['PATH_INFO'] = path_info[len('/api/index.py'):] or '/'
        elif path_info.startswith('/api/index'):
            environ['PATH_INFO'] = path_info[len('/api/index'):] or '/'
            
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelWSGIHandler(app.wsgi_app)
