import aws_cdk as cdk

from aws_cdk import (
    aws_iam as iam,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_secretsmanager as sm,
    aws_autoscaling as autoscaling,
    aws_kms as kms,
    aws_ssm as ssm,
)
from constructs import Construct

import common.functions

class DbStack(cdk.Stack):

    def __init__(self, scope: Construct, id: str, props, constants, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Unpack constants
        common.functions.unpack_constants_dict(self, constants)
        VPC = props['vpc']
        INSTANCE_ASG_NAME = props['instance_asg_name']

        # Security Group for the DB
        #db_sg = ec2.SecurityGroup(
        #        self,
        #        id='db_sg',
        #        vpc=VPC,
        #        security_group_name='{0}sg_rds'.format(self.APP_NAME)
        #)

        #db_sg.add_ingress_rule(
        #    peer=ec2.SecurityGroup.from_security_group_id(
        #        self,
        #        id='db_sg_rule_traffic_from_application_layer',
        #        security_group_id=props['application_layer_sg_id']),
        #    connection=ec2.Port.tcp(int(constants.get('DB_PORT')))
        #)

        # RDS DB Settings
        engine = ''
        hosted_rotation = ''
        if self.DATABASE_ENGINE == 'mysql':
            engine = rds.DatabaseInstanceEngine.mysql(
                version=rds.MysqlEngineVersion.VER_8_0_21
            )
            hosted_rotation = sm.HostedRotation.mysql_single_user(vpc=VPC)
        if self.DATABASE_ENGINE == 'sqlserver':
            engine = rds.DatabaseInstanceEngine.sql_server_se(
                version=rds.SqlServerEngineVersion.VER_15
            )
            hosted_rotation = sm.HostedRotation.sql_server_single_user(vpc=VPC)
        if self.DATABASE_ENGINE == 'mariadb':
            engine = rds.DatabaseInstanceEngine.maria_db(
                version=rds.MariaDbEngineVersion.VER_10_4_13
            )
            hosted_rotation = sm.HostedRotation.maria_db_single_user(vpc=VPC)

        # Default to snapshot option on db deletion
        database_removal_policy = cdk.RemovalPolicy.SNAPSHOT
        if self.DATABASE_REMOVAL_POLICY == 'retain':
            database_removal_policy = cdk.RemovalPolicy.RETAIN
        elif self.DATABASE_REMOVAL_POLICY == 'destroy':
            database_removal_policy = cdk.RemovalPolicy.DESTROY

        # Choose between service CMK and Customer Managed CMK
        if self.DATABASE_ENCRYPTION_KEY == 'RDS_SERVICE_KEY':
            db_kms_key_arn = None
        else:
            db_kms_key_arn = kms.Key.from_key_arn(
                "db_kms_key_arn",
                key_arn=self.DATABASE_ENCRYPTION_KEY
            )

        # TODO: Use Option Groups to harden DB Instances
        # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.SQLServer.Options.html

        # Create RDS DB instance
        db = rds.DatabaseInstance(
            self,
            id='db',
            engine=engine,
            vpc=VPC,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2,
                ec2.InstanceSize.LARGE
            ),
            removal_policy=database_removal_policy,
            storage_encrypted=True,
            storage_encryption_key=db_kms_key_arn,
            database_name=self.APP_NAME.replace('-', '')
            #security_groups=[db_sg]
        )

        # Allow Traffic from Applicaiton Instances to DB
        db.connections.allow_default_port_from(
            ec2.SecurityGroup.from_security_group_id(
                self,
                id='application_layer_sg',
                security_group_id=props['application_layer_sg_id']
            )
        )

        # Rotate secret every 30 days
        if self.SECRET_ROTATION == True:
            db.secret.add_rotation_schedule(
                'RotationSchedule',
                hosted_rotation=hosted_rotation
            )
            db.connections.allow_default_port_from(hosted_rotation)

        # Allow App Instances to read DB secret
        application_layer_instance_profile_role = iam.Role.from_role_arn(
            self,
            'ApplicationLayerInstanceProfileRole',
            role_arn=props['application_layer_instance_profile_role_arn']
        )
        db.secret.grant_read(
            grantee=application_layer_instance_profile_role
        )

        # Parameter so that Instances know the name of the
        # secret value to get to connect to DB
        db_secret_id_ssm_parameter = ssm.StringParameter(
            self,
            'DbSecretIdSsmParameter',
            parameter_name='/{0}/db_secret'.format(self.APP_NAME),
            string_value=str(db.secret.secret_name),
            description='Name of Secret App should pull for DB access'
        )
        db_secret_id_ssm_parameter.grant_read(application_layer_instance_profile_role)

        application_instance_asg = autoscaling.AutoScalingGroup.from_auto_scaling_group_name(
            self,
            'InstanceAsgImport',
            auto_scaling_group_name=INSTANCE_ASG_NAME
        )
