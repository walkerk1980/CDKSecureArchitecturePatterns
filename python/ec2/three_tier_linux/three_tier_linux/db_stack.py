from aws_cdk import (
    aws_iam as iam,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_secretsmanager,
    core
)

import common.functions

class DbStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, constants, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Unpack constants
        common.functions.unpack_constants_dict(self, constants)

        # Security Group for the DB
        db_sg = ec2.SecurityGroup(
                self,
                id="db_sg",
                vpc=props['vpc'],
                security_group_name="{0}sg_rds".format(self.APP_NAME)
        )

        db_sg.add_ingress_rule(
            peer=ec2.SecurityGroup.from_security_group_id(
                self,
                id='db_sg_rule_traffic_from_application_layer',
                security_group_id=props['application_layer_sg_id']),
            connection=ec2.Port.tcp(int(constants.get('DB_PORT')))
        )

        engine = ''
        if self.DATABASE_ENGINE == 'mysql':
            engine = rds.DatabaseInstanceEngine.mysql(
                version=rds.MysqlEngineVersion.VER_8_0_21
            )
        if self.DATABASE_ENGINE == 'sqlserver':
            engine = rds.DatabaseInstanceEngine.sql_server_se(
                version=rds.SqlServerEngineVersion.VER_15
            )
        if self.DATABASE_ENGINE == 'mariadb':
            engine = rds.DatabaseInstanceEngine.maria_db(
                version=rds.MariaDbEngineVersion.VER_10_4_13
            )

        db = rds.DatabaseInstance(
            self,
            id="db",
            engine=engine,
            vpc=props['vpc'],
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2,
                ec2.InstanceSize.LARGE
            ),
            removal_policy=core.RemovalPolicy.DESTROY,
            security_groups=[db_sg]
        )

        #db_secret_rotation_schedule = Secret.

        #db.secret.add_rotation_schedule(automatically_after=Duration.days(30))
        
        db.secret.grant_read(
            grantee=iam.Role.from_role_arn(
                self,
                'application_layer_instance_profile_role',
                role_arn=props['application_layer_instance_profile_role_arn']
            )
        )