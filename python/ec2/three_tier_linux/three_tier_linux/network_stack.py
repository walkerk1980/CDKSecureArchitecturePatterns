from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_certificatemanager as acm,
    aws_route53 as r53,
    aws_route53_targets as r53_targets,
    core
)

import common.functions

class NetworkStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, props, constants: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Unpack constants
        common.functions.unpack_constants_dict(self, constants)

        # VPC
        if self.VPC == 'create_new_vpc':
            vpc = ec2.Vpc(self, '{0}VPC'.format(self.APP_NAME),
                nat_gateways=3,
                subnet_configuration=[
                    ec2.SubnetConfiguration(name='public',subnet_type=ec2.SubnetType.PUBLIC),
                    ec2.SubnetConfiguration(name='private',subnet_type=ec2.SubnetType.PRIVATE),
                ]
            )
        else:
            vpc = ec2.Vpc.from_lookup(
                "imported_vpc",
                vpc_name=self.VPC
            )

        # This will export the VPC's ID in CloudFormation under the key
        # 'vpcid'
        core.CfnOutput(self, 'vpcid', value=vpc.vpc_id)

        # Prepares output attributes to be passed into other stacks
        # In this case, it is our VPC and subnets.
        self.output_props = props.copy()
        self.output_props['vpc'] = vpc
        self.output_props['public_subnets'] = vpc.public_subnets
        self.output_props['private_subnets'] = vpc.private_subnets

        @property
        def outputs(self):
            return self.output_props
