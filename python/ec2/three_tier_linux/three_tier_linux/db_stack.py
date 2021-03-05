from aws_cdk import (
    aws_iam as iam,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_secretsmanager as sm,
    core
)

import common.functions

class DbStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, constants, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Unpack constants
        common.functions.unpack_constants_dict(self, constants)
        VPC = props['vpc']

        # Security Group for the DB
        #db_sg = ec2.SecurityGroup(
        #        self,
        #        id="db_sg",
        #        vpc=VPC,
        #        security_group_name="{0}sg_rds".format(self.APP_NAME)
        #)

        #db_sg.add_ingress_rule(
        #    peer=ec2.SecurityGroup.from_security_group_id(
        #        self,
        #        id='db_sg_rule_traffic_from_application_layer',
        #        security_group_id=props['application_layer_sg_id']),
        #    connection=ec2.Port.tcp(int(constants.get('DB_PORT')))
        #)

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

        db = rds.DatabaseInstance(
            self,
            id="db",
            engine=engine,
            vpc=VPC,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2,
                ec2.InstanceSize.LARGE
            ),
            removal_policy=core.RemovalPolicy.DESTROY,
            #security_groups=[db_sg]
        )

        db.connections.allow_default_port_from(
            ec2.SecurityGroup.from_security_group_id(
                self,
                id='application_layer_sg',
                security_group_id=props['application_layer_sg_id']
            )
        )

        db.secret.add_rotation_schedule(
            'rotation_schedule',
            hosted_rotation=hosted_rotation
        )
        
        db.connections.allow_default_port_from(hosted_rotation)

        db.secret.grant_read(
            grantee=iam.Role.from_role_arn(
                self,
                'application_layer_instance_profile_role',
                role_arn=props['application_layer_instance_profile_role_arn']
            )
        )