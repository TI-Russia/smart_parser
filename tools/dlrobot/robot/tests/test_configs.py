from dlrobot.common.robot_config import TRobotConfig
from unittest import TestCase


class TestConfigType(TestCase):
    def test_config_type(self):
        test = TRobotConfig.read_by_config_type("test")
        prel = TRobotConfig.read_by_config_type("preliminary")
        prod = TRobotConfig.read_by_config_type("prod")
        self.assertLess(test.get_dlrobot_total_timeout(), prel.get_dlrobot_total_timeout())
        self.assertLess(prel.get_dlrobot_total_timeout(), prod.get_dlrobot_total_timeout())
