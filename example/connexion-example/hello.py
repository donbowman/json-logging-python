#!/usr/bin/env python3

import connexion
import json_logging


def post_greeting(name: str) -> str:
    return 'Hello {name}'.format(name=name)


def create():
    app = connexion.FlaskApp(__name__, port=9090, specification_dir='openapi/')
    json_logging.ENABLE_JSON_LOGGING = True
    json_logging.init(framework_name='connexion')
    json_logging.init_request_instrument(app)

    app.add_api('helloworld-api.yaml', arguments={'title': 'Hello World Example'})
    return app


if __name__ == '__main__':
    app = create()
    app.run()
