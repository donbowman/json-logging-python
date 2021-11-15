# register flask support
# noinspection PyPep8
import json_logging.framework.flask as flask_support
from json_logging import util, RequestAdapter, ResponseAdapter, AppRequestInstrumentationConfigurator, \
    FrameworkConfigurator, _framework_support_map, ENABLE_JSON_LOGGING_DEBUG, _logger


def register_framework_support(name, app_configurator, app_request_instrumentation_configurator, request_adapter_class,
                               response_adapter_class):
    """
    register support for a framework

    :param name: name of framework
    :param app_configurator: app pre-configurator class
    :param app_request_instrumentation_configurator: app configurator class
    :param request_adapter_class: request adapter class
    :param response_adapter_class: response adapter class
    """
    if not name:
        raise RuntimeError("framework name can not be null or empty")

    util.validate_subclass(request_adapter_class, RequestAdapter)
    util.validate_subclass(response_adapter_class, ResponseAdapter)
    util.validate_subclass(app_request_instrumentation_configurator, AppRequestInstrumentationConfigurator)
    if app_configurator is not None:
        util.validate_subclass(app_configurator, FrameworkConfigurator)

    name = name.lower()
    if name in _framework_support_map:
        ENABLE_JSON_LOGGING_DEBUG and _logger.warning("Re-register framework %s", name)
    _framework_support_map[name] = {
        'app_configurator': app_configurator,
        'app_request_instrumentation_configurator': app_request_instrumentation_configurator,
        'request_adapter_class': request_adapter_class,
        'response_adapter_class': response_adapter_class
    }


register_framework_support('flask', None, flask_support.FlaskAppRequestInstrumentationConfigurator,
                           flask_support.FlaskRequestAdapter,
                           flask_support.FlaskResponseAdapter)

# register sanic support
# noinspection PyPep8
from json_logging.framework.sanic import SanicAppConfigurator, SanicAppRequestInstrumentationConfigurator, \
    SanicRequestAdapter, SanicResponseAdapter

register_framework_support('sanic', SanicAppConfigurator,
                           SanicAppRequestInstrumentationConfigurator,
                           SanicRequestAdapter,
                           SanicResponseAdapter)

# register quart support
# noinspection PyPep8
import json_logging.framework.quart as quart_support

register_framework_support('quart', None, quart_support.QuartAppRequestInstrumentationConfigurator,
                           quart_support.QuartRequestAdapter,
                           quart_support.QuartResponseAdapter)

# register connexion support
# noinspection PyPep8
import json_logging.framework.connexion as connexion_support

register_framework_support('connexion', None, connexion_support.ConnexionAppRequestInstrumentationConfigurator,
                           connexion_support.ConnexionRequestAdapter,
                           connexion_support.ConnexionResponseAdapter)

# register FastAPI support
import json_logging.framework.fastapi as fastapi_support

if fastapi_support.is_fastapi_present():
    register_framework_support('fastapi', app_configurator=None,
                               app_request_instrumentation_configurator=fastapi_support.FastAPIAppRequestInstrumentationConfigurator,
                               request_adapter_class=fastapi_support.FastAPIRequestAdapter,
                               response_adapter_class=fastapi_support.FastAPIResponseAdapter)
