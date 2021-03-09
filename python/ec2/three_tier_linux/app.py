#!/usr/bin/env python3
from aws_cdk import (
    core
)

from three_tier_linux.frontend_stack import FrontendStack
from three_tier_linux.network_stack import NetworkStack
from three_tier_linux.db_stack import DbStack

# Constants
APP_NAME = 'three-tier-linux'
APP_DOMAIN = 'cdk.preprod.example.net'
# Hosted Zone must already exist
# to create ACM Certificate DNS validation CNAME
# and www A (Alias) resource records
HOSTED_ZONE_DOMAIN = 'preprod.example.net'
DEPLOYMENT_ACCOUNT='123456789012'
DEPLOYMENT_REGION='us-west-2'
BACKEND_PORT=80
# choices ['mysql', 'sqlserver', 'mariadb']
DATABASE_ENGINE='mysql'
# choices ['retain', 'snapshot', 'destroy']
DATABASE_REMOVAL_POLICY='destroy'
SECRET_ROTATION=False
# choices ['create_new_vpc', 'existing_vpc_name']
VPC='create_new_vpc'

constants = {}
constants.update({'APP_NAME': APP_NAME})
constants.update({'APP_DOMAIN': APP_DOMAIN})
constants.update({'HOSTED_ZONE_DOMAIN': HOSTED_ZONE_DOMAIN})
constants.update({'DEPLOYMENT_ACCOUNT': DEPLOYMENT_ACCOUNT})
constants.update({'DEPLOYMENT_REGION': DEPLOYMENT_REGION})
constants.update({'BACKEND_PORT': BACKEND_PORT})
constants.update({'DATABASE_ENGINE': DATABASE_ENGINE})
constants.update({'DATABASE_REMOVAL_POLICY': DATABASE_REMOVAL_POLICY})
constants.update({'SECRET_ROTATION': SECRET_ROTATION})
constants.update({'VPC': VPC})

props = {'namespace': 'NetworkStack'}

app = core.App()

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

db_stack = DbStack(
    app,
    '{}-DbStack'.format(APP_NAME),
    frontend_stack.output_props,
    constants,
    env=core.Environment(
        account=DEPLOYMENT_ACCOUNT,
        region=DEPLOYMENT_REGION
    )
)

db_stack.add_dependency(frontend_stack)

app.synth()
