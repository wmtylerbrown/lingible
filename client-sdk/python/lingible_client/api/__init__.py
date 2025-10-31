# flake8: noqa

if __import__("typing").TYPE_CHECKING:
    # import apis into api package
    from lingible_client.api.admin_api import AdminApi
    from lingible_client.api.quiz_api import QuizApi
    from lingible_client.api.slang_api import SlangApi
    from lingible_client.api.system_api import SystemApi
    from lingible_client.api.translation_api import TranslationApi
    from lingible_client.api.trending_api import TrendingApi
    from lingible_client.api.user_api import UserApi
    from lingible_client.api.webhooks_api import WebhooksApi

else:
    from lazy_imports import LazyModule, as_package, load

    load(
        LazyModule(
            *as_package(__file__),
            """# import apis into api package
from lingible_client.api.admin_api import AdminApi
from lingible_client.api.quiz_api import QuizApi
from lingible_client.api.slang_api import SlangApi
from lingible_client.api.system_api import SystemApi
from lingible_client.api.translation_api import TranslationApi
from lingible_client.api.trending_api import TrendingApi
from lingible_client.api.user_api import UserApi
from lingible_client.api.webhooks_api import WebhooksApi

""",
            name=__name__,
            doc=__doc__,
        )
    )
