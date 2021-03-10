import os.path

from aws_cdk.aws_s3_assets import Asset

from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    # aws_elasticloadbalancingv2_targets as elbv2_targets,
    aws_certificatemanager as acm,
    aws_route53 as r53,
    aws_route53_targets as r53_targets,
    aws_autoscaling as autoscaling,
    aws_kms as kms,
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

        # Custom Image
        ami_owner = self.BASE_AMI_ACCOUNT
        if ami_owner == 'SELF':
            ami_owner = None

        base_ami = amzn_linux
        if self.BASE_AMI_NAME != 'AWS_PROVIDED':
            custom_ami = ec2.LookupMachineImage(
                name=self.BASE_AMI_NAME,
                owners=[ami_owner],
                windows=False,
            )
            base_ami = custom_ami

        # Instance Role and SSM Managed Policy
        role = iam.Role(self, 'InstanceSSM', assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'))

        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'))
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMDirectoryServiceAccess'))
        role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_name(self, id='LogsPolicy',
                managed_policy_name='CloudwatchLogsInstanceProfile'
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

        # ACM Certificate for application frontend
        acm_cert = acm.Certificate(
            self, '{}Certificate'.format(self.APP_NAME),
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
        alb = elbv2.ApplicationLoadBalancer(self, '{0}LoadBalancer'.format(self.APP_NAME),
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg
        )

        # Add http listerner and redirect to https
        http_listener = alb.add_listener(
            id='http',
            port=80
        )

        http_listener.add_redirect_response(
            'redirect_http_to_https',
            status_code='HTTP_301',
            #host='#{host}',
            #path='/#{path}',
            #query='#{query}',
            port='443',
            protocol='HTTPS'
        )

        # Allow traffic from ALB SG to Instance SG
        instance_sg.add_ingress_rule(
            description='Allow HTTP traffic from ALB',
            peer=alb_sg,
            connection=ec2.Port.tcp(self.BACKEND_PORT)
        )

        # DNS record for ALB
        hosted_zone = r53.HostedZone.from_lookup(
            self, 'AppHostedZone',
            domain_name=self.HOSTED_ZONE_DOMAIN
        )

        # Create an Alias record of www to point at ALB
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

        # Instance AutoScalingGroup
        instance_asg = autoscaling.AutoScalingGroup(
            self,
            'instance_asg',
            vpc=vpc,
            instance_type=ec2.InstanceType('t3.nano'),
            role=role,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE),
            security_group=instance_sg,
            machine_image=base_ami,
            health_check=autoscaling.HealthCheck.elb(grace=core.Duration.seconds(150)),
            min_capacity=2,
            max_capacity=7,
            max_instance_lifetime=core.Duration.days(7)
        )

        # Health check for Target Group
        instance_tg_health_check = elbv2.HealthCheck(
            protocol=elbv2.Protocol('HTTP'),
            path='/',
            port='traffic-port',
            healthy_threshold_count=2,
            unhealthy_threshold_count=2,
            timeout=core.Duration.seconds(5),
            interval=core.Duration.seconds(30),
            healthy_http_codes='200',
        )

        # Application Target Group
        instance_tg = elbv2.ApplicationTargetGroup(
            self,
            '{0}TargetGroup'.format(self.APP_NAME),
            port=self.BACKEND_PORT,
            vpc=vpc,
            targets=[instance_asg],
            health_check=instance_tg_health_check
        )

        # Add HTTPS listener to ALB
        https_listener = alb.add_listener(
            id='https',
            port=443,
            certificates=[acm_cert],
            default_target_groups=[instance_tg],
            ssl_policy=elbv2.SslPolicy.FORWARD_SECRECY_TLS12_RES_GCM
        )

        # Script in S3 as Asset to Instance Userdata
        asset = Asset(self, '{0}Asset'.format(self.APP_NAME), path=os.path.join(dirname, 'configure.sh'))
        local_path = instance_asg.user_data.add_s3_download_command(
            bucket=asset.bucket,
            bucket_key=asset.s3_object_key
        )
        instance_asg.user_data.add_execute_file_command(
            file_path=local_path
        )
        asset.grant_read(instance_asg.role)

        # Prepares output attributes to be passed into other stacks
        self.output_props = props.copy()
        self.output_props['application_layer_sg_id'] = instance_sg.security_group_id
        self.output_props['application_layer_instance_profile_role_arn'] = role.role_arn
        self.output_props['instance_asg_name'] = instance_asg.auto_scaling_group_name

        @property
        def outputs(self):
            return self.output_props
