from TemplateEngine import TemplateEngine

class AntoniiFramework:
    def __init__(self):
        self.routes = {}
        self.dynamic_routes = {}

    def add_route(self, method, path, handler):
        if '<' in path and '>' in path:
            pattern_parts, param_names, param_types = self.splitter(path)
            self.dynamic_routes.setdefault(method, []).append(
                (pattern_parts, param_names, param_types, handler)
            )
        else:
            self.routes[(method, path)] = handler

    def splitter(self, path: str):
        parts = path.split('/')
        param_names = []
        param_types = []
        for part in parts:
            if part.startswith('<') and part.endswith('>'):
                inside = part[1:-1]
                if ':' in inside:
                    name, type_name = inside.split(':', 1)
                else:
                    name, type_name = inside, 'str'
                param_names.append(name)
                param_types.append(type_name)
        return parts, param_names, param_types

    def get(self, path):
        def decorator(fn):
            self.add_route('GET', path, fn)
            return fn
        return decorator

    def post(self, path):
        def decorator(fn):
            self.add_route('POST', path, fn)
            return fn
        return decorator

    def __call__(self, environ, start_response):
        method = environ.get('REQUEST_METHOD', 'GET').upper()
        path = environ.get('PATH_INFO', '/')
        handler = self.routes.get((method, path))
        params_kwargs = {}
        saw_type_conversion_error = False

        if handler is None:
            path_parts = path.split('/')
            for pattern_parts, param_names, param_types, candidate in self.dynamic_routes.get(method, []):
                if len(pattern_parts) != len(path_parts):
                    continue
                captured = {}
                matched = True
                param_index = 0
                for pattern_part, path_part in zip(pattern_parts, path_parts):
                    if pattern_part.startswith('<') and pattern_part.endswith('>'):
                        name = param_names[param_index]
                        type = param_types[param_index]
                        param_index += 1
                        try:
                            if type == 'int':
                                value = int(path_part)
                            elif type in ('str', '', None):
                                value = path_part
                            else:
                                value = path_part
                            captured[name] = value
                        except Exception:
                            matched = False
                            saw_type_conversion_error = True
                            break
                    else:
                        if pattern_part != path_part:
                            matched = False
                            break
                if matched:
                    handler = candidate
                    params_kwargs = captured
                    break

        if handler is None and saw_type_conversion_error:
            start_response('400 Bad Request', [('Content-Type', 'text/plain; charset=utf-8')])
            return [b'Bad Request']

        if handler is None:
            start_response('404 Not Found', [('Content-Type', 'text/plain; charset=utf-8')])
            return [b'Not Found']

        if method == 'POST':
            try:
                length = int(environ.get('CONTENT_LENGTH', 0) or 0)
            except (ValueError, TypeError):
                length = 0
            body = environ['wsgi.input'].read(length) if length > 0 else b''
            args = (body.decode('utf-8'),)
        else:
            args = ()
        result = handler(*args, **params_kwargs) if params_kwargs else handler(*args)

        if isinstance(result, bytes):
            body_bytes = result
        else:
            body_bytes = str(result).encode('utf-8')

        start_response('200 OK', [
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Length', str(len(body_bytes))),
        ])
        return [body_bytes]

app = AntoniiFramework()
template = TemplateEngine()
def _html(str):
    return str

@app.get('/hello/<name>/<age:int>/<city>')
def hello_person(name, age, city):
    context = {"name": name, "age": age, "city": city, "nickname": "Guest"}
    html = template.render("templates/greeting.html", context)
    return _html(html)

@app.get('/profile/<name>/<age:int>')
def profile(name, age):
    context = {"name": name, "age": age}
    html = template.render("templates/profile.html", context)
    return _html(html)

@app.get('/status/<temperature:int>')
def status(temperature):
    context = {"temperature": temperature}
    html = template.render("templates/status.html", context)
    return _html(html)

@app.get('/tasks')
def tasks():
    context = {"tasks": ["Write report", "Gym", "Call mom", "Read 10 pages"]}
    html = template.render("templates/tasks.html", context)
    return _html(html)