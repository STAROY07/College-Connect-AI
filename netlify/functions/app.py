import sys
import os
import io
import base64
import urllib.parse

# 1. Setup paths so root modules, templates, data, and configs are accessible
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    os.chdir(root_dir)
except Exception:
    pass

from app import app

# Pure Python WSGI to AWS Lambda / Netlify Function Adapter
def custom_wsgi_handler(wsgi_app, event, context):
    path = event.get('path') or '/'
    
    # Strip Netlify function prefixes if present in path
    if path.startswith('/.netlify/functions/app'):
        path = path[len('/.netlify/functions/app'):] or '/'
    elif path.startswith('/.netlify/functions/index'):
        path = path[len('/.netlify/functions/index'):] or '/'

    http_method = event.get('httpMethod', 'GET')
    headers = event.get('headers') or {}
    
    # Query parameters handling
    query_params = event.get('queryStringParameters') or {}
    query_string = urllib.parse.urlencode(query_params)
    
    # Body decoding
    body = event.get('body') or ''
    if event.get('isBase64Encoded', False):
        try:
            body_bytes = base64.b64decode(body)
        except Exception:
            body_bytes = body.encode('utf-8') if isinstance(body, str) else body
    else:
        body_bytes = body.encode('utf-8') if isinstance(body, str) else (body or b'')

    environ = {
        'REQUEST_METHOD': http_method,
        'SCRIPT_NAME': '',
        'PATH_INFO': urllib.parse.unquote(path),
        'QUERY_STRING': query_string,
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '443',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': headers.get('x-forwarded-proto', 'https'),
        'wsgi.input': io.BytesIO(body_bytes),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'CONTENT_LENGTH': str(len(body_bytes)),
        'CONTENT_TYPE': headers.get('content-type', headers.get('Content-Type', '')),
    }

    # Pass HTTP headers to WSGI environment
    for key, value in headers.items():
        key_upper = key.upper().replace('-', '_')
        if key_upper not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            environ[f'HTTP_{key_upper}'] = str(value)

    response_headers = []
    response_status = [200]

    def start_response(status, headers_list, exc_info=None):
        try:
            response_status[0] = int(status.split(' ')[0])
        except Exception:
            response_status[0] = 200
        response_headers.extend(headers_list)

    response_body_chunks = wsgi_app(environ, start_response)
    response_body = b''.join(response_body_chunks)

    res_headers = {}
    multi_value_headers = {}
    for k, v in response_headers:
        if k.lower() == 'set-cookie':
            multi_value_headers.setdefault(k, []).append(v)
        else:
            res_headers[k] = v

    content_type = res_headers.get('Content-Type', res_headers.get('content-type', ''))
    is_binary = not (
        content_type.startswith('text/') or
        'json' in content_type or
        'javascript' in content_type or
        'xml' in content_type or
        'html' in content_type
    )

    result = {
        'statusCode': response_status[0],
        'headers': res_headers,
    }
    if multi_value_headers:
        result['multiValueHeaders'] = multi_value_headers

    if is_binary:
        result['isBase64Encoded'] = True
        result['body'] = base64.b64encode(response_body).decode('utf-8')
    else:
        try:
            result['body'] = response_body.decode('utf-8')
            result['isBase64Encoded'] = False
        except UnicodeDecodeError:
            result['isBase64Encoded'] = True
            result['body'] = base64.b64encode(response_body).decode('utf-8')

    return result

def handler(event, context):
    try:
        import serverless_wsgi
        return serverless_wsgi.handle_request(app, event, context)
    except Exception:
        return custom_wsgi_handler(app.wsgi_app, event, context)
