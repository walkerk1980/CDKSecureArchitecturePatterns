import json
import pytest

from aws_cdk import core
from three_tier_linux.three_tier_linux_stack import ThreeTierLinuxStack


def get_template():
    app = core.App()
    ThreeTierLinuxStack(app, "three-tier-linux")
    return json.dumps(app.synth().get_stack("three-tier-linux").template)


def test_sqs_queue_created():
    assert("AWS::SQS::Queue" in get_template())


def test_sns_topic_created():
    assert("AWS::SNS::Topic" in get_template())
