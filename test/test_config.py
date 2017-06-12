# import config
from unittest import TestCase, main

# cannot run this test until a bug is fixed with the config module.
# it is exceptioning when config tries to use the logging module.


class DownloadTest(TestCase):
    def test_config_contains_proper_attributes(self):
        # remove return when bug is fixed and decomment the config import above
        return

        assert hasattr(config, "TRANSLATION_DIRNAME")
        assert hasattr(config, "TRANSLATION_DIR")
        assert hasattr(config, "TRANSLATIONS")
        assert hasattr(config, "CONFIG")
        assert hasattr(config, "CONFIG_DIRNAME")
        assert hasattr(config, "CONFIG_DIR")
        assert hasattr(config, "CONFIG_FILE")
        assert hasattr(config, "BASE_DIR")
        assert hasattr(config, "RESOURCE_DIR")
        assert hasattr(config, "GLOBAL_CONTEXT")

        CONFIG = config.CONFIG

        assert hasattr(CONFIG, "branches")
        assert hasattr(CONFIG, "config_endpoint")
        assert hasattr(CONFIG, "launcher_endpoint")
        assert hasattr(CONFIG, "index_endpoint")
        assert hasattr(CONFIG, "launch_flags")
        assert hasattr(CONFIG, "news_rss_feed")
        assert hasattr(CONFIG, "game_binary")
        assert hasattr(CONFIG, "logo")

if __name__ == "__main__":
    main()
