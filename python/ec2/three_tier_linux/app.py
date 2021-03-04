#!/usr/bin/env python3
from aws_cdk import (
    core
)

from three_tier_linux.frontend_stack import FrontendStack
from three_tier_linux.network_stack import NetworkStack

# Constants
APP_NAME = 'three-tier-linux'
APP_DOMAIN = 'cdk.waftest.example.net'
HOSTED_ZONE_DOMAIN = 'waftest.example.net'
DEPLOYMENT_ACCOUNT='123456789012'
DEPLOYMENT_REGION='us-west-2'
BACKEND_PORT=80
DB_PORT=1433
#DATABASE_ENGINE = rds.DatabaseInstanceEngine.sql_server_se(
#        version=rds.SqlServerEngineVersion.VER_15
#    ),

constants = {}
constants.update({'APP_NAME': APP_NAME})
constants.update({'APP_DOMAIN': APP_DOMAIN})
constants.update({'HOSTED_ZONE_DOMAIN': HOSTED_ZONE_DOMAIN})
constants.update({'DEPLOYMENT_ACCOUNT': DEPLOYMENT_ACCOUNT})
constants.update({'DEPLOYMENT_REGION': DEPLOYMENT_REGION})
constants.update({'BACKEND_PORT': BACKEND_PORT})
constants.update({'DB_PORT': DB_PORT})

#constants.update({'DATABASE_ENGINE': DATABASE_ENGINE})

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

#db_stack = 

app.synth()
