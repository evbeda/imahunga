import flask
from flask_cors import CORS
import route as route


class MainApp:
    def __init__(self):
        self.flask_app = flask.Flask(__name__,static_folder = '/public')
        CORS(self.flask_app, support_credentials=True, automatic_options = True)
        self._init_routes()
        self._init_api()

    def _init_routes(self):
        @self.flask_app.route('/<path:path>')
        def api_index(path):
            return flask.send_from_directory('/public', path)

    def get_flask_app(self):
        return self.flask_app

    def _init_api(self):
        route.init(self.flask_app)

    def start(self):
        print("started")
        self.flask_app.run()


main_app = MainApp()
# main_app.start()
app = main_app.flask_app
