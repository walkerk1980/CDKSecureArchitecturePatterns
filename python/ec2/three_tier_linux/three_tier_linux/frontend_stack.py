import os.path

from aws_cdk.aws_s3_assets import Asset

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

class FrontendStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, props, constants: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Unpack constants
        common.functions.unpack_constants_dict(self, constants)

        dirname = os.path.dirname(__file__)

        # Unpack props
        vpc = props['vpc']

        # AMIs
        amzn_linux = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
        )

        # AMI
        windows = ec2.MachineImage.latest_windows(
            version=ec2.WindowsVersion.WINDOWS_SERVER_2019_ENGLISH_CORE_BASE
        )

        base_ami = amzn_linux

        # Instance Role and SSM Managed Policy
        role = iam.Role(self, "InstanceSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))

        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMDirectoryServiceAccess"))
        role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_name(self, id='LogsPolicy',
                managed_policy_name="CloudwatchLogsInstanceProfile"
            )
        )

        # Security Group for Instance
        instance_sg = ec2.SecurityGroup(
            self, '{0}InstanceSecurityGroup'.format(self.APP_NAME),
            description='{0}InstanceSecurityGroup'.format(self.APP_NAME),
            vpc=vpc,
            security_group_name='{0}InstanceSecurityGroup'.format(self.APP_NAME),
            allow_all_outbound=True
        )

        # TODO AutoScalingGroups instead of Instances
        # Instances
        instance1 = ec2.Instance(self, "{0}Instance1".format(self.APP_NAME),
            instance_type=ec2.InstanceType("t3.nano"),
            machine_image=base_ami,
            vpc=vpc,
            role = role,
            security_group=instance_sg
        )

        instance2 = ec2.Instance(self, "{0}Instance2".format(self.APP_NAME),
            instance_type=ec2.InstanceType("t3.nano"),
            machine_image=base_ami,
            vpc=vpc,
            role = role,
            security_group=instance_sg
        )

        instances = [ instance1, instance2]

        # Script in S3 as Asset
        asset = Asset(self, "{0}Asset".format(self.APP_NAME), path=os.path.join(dirname, "configure.sh"))
        for instance in instances:
            local_path = instance.user_data.add_s3_download_command(
                bucket=asset.bucket,
                bucket_key=asset.s3_object_key
            )

        # Userdata executes script from S3
        for instance in instances:
            instance.user_data.add_execute_file_command(
                file_path=local_path
            )
            asset.grant_read(instance.role)

        # ACM Certificate for application frontend
        acm_cert = acm.Certificate(
            self, "{}Certificate".format(self.APP_NAME),
            domain_name=self.APP_DOMAIN,
            subject_alternative_names=['www.{}'.format(self.APP_DOMAIN)],
            validation_method=acm.ValidationMethod.DNS
        )

        #Security Group for ALB
        alb_sg = ec2.SecurityGroup(
            self, '{0}ALBSecurityGroup'.format(self.APP_NAME),
            vpc=vpc,
            security_group_name='{0}ALBSecurityGroup'.format(self.APP_NAME),
            allow_all_outbound=True
        )

        # Application Load Balancer to front Instance
        alb = elbv2.ApplicationLoadBalancer(self, "{0}LoadBalancer".format(self.APP_NAME),
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg
        )

        target_group = elbv2.ApplicationTargetGroup(self, "{0}TargetGroup".format(self.APP_NAME),
            port=self.BACKEND_PORT,
            vpc=vpc
        )

        # Add standalone instances to target group for now
        for instance in instances:
            target_group.add_target(
                elbv2.InstanceTarget(instance.instance_id)
            )

        alb.add_listener(
            id='http',
            default_target_groups=[target_group],
            port=80
        )

        alb.add_listener(
            id='https',
            default_target_groups=[target_group],
            port=443,
            certificates=[acm_cert]
        )

        # Allow traffic from ALB SG to Instance SG
        instance_sg.add_ingress_rule(
            description='Allow HTTP traffic from ALB',
            peer=alb_sg,
            connection=ec2.Port.tcp(self.BACKEND_PORT)
        )

        # DNS record for ALB
        hosted_zone = r53.HostedZone.from_lookup(
            self, "AppHostedZone",
            domain_name=self.HOSTED_ZONE_DOMAIN
        )

        alb_target = r53_targets.LoadBalancerTarget(alb)
        alb_record_target = r53.RecordTarget(
            alias_target=alb_target
        )

        www_alias_record = r53.ARecord(
            self, '{}AliasRecord'.format(self.APP_NAME),
            record_name='www.{0}'.format(self.APP_DOMAIN),
            target=alb_record_target,
            zone=hosted_zone
        )

        # TODO
        # Redirect HTTP to HTTPS
        #https_redirect = elbv2.ApplicationListenerRule(
        #    self, 'HTTPSRedirect',
        #    priority=1,
        #    listener=
        #)

        # This will export the VPC's ID in CloudFormation under the key
        # 'vpcid'
        #core.CfnOutput(self, "vpcid", value=vpc.vpc_id)

        # Prepares output attributes to be passed into other stacks
        # In this case, it is our VPC and subnets.
        self.output_props = props.copy()
        self.output_props['application_layer_sg_id'] = instance_sg.security_group_id
        self.output_props['application_layer_instanc_profile_role_arn'] = role.role_arn

        @property
        def outputs(self):
            return self.output_props
