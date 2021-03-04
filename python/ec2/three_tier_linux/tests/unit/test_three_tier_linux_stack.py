import json
import pytest

from aws_cdk import core
from three_tier_linux.frontend_stack import FrontendStack
from three_tier_linux.network_stack import NetworkStack

from app import props
from app import constants
from app import APP_NAME
from app import DEPLOYMENT_ACCOUNT
from app import DEPLOYMENT_REGION

def get_templates():
    app = core.App()
    templates = {}
    network_stack = NetworkStack(
        app,
        '{}-NetworkStack'.format(APP_NAME),
        props,
        constants,
        env=core.Environment(
            account=DEPLOYMENT_ACCOUNT,
            region=DEPLOYMENT_REGION
        )
    )
    frontend_stack = FrontendStack(
        app,
        '{}-FrontendStack'.format(APP_NAME),
        network_stack.output_props,
        constants,
        env=core.Environment(
            account=DEPLOYMENT_ACCOUNT,
            region=DEPLOYMENT_REGION
        )
    )
    frontend_stack.add_dependency(network_stack)
    templates.update({'NetworkStack': json.dumps(app.synth().get_stack('three-tier-linux-NetworkStack').template)})
    templates.update({'FrontendStack': json.dumps(app.synth().get_stack('three-tier-linux-FrontendStack').template)})
    return templates

def test_vpc_created():
    assert("AWS::EC2::VPC" in get_templates().get('NetworkStack'))

def test_instance_created():
    assert("AWS::EC2::Instance" in get_templates().get('FrontendStack'))