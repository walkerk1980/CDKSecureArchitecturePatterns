from aws_cdk import (
    aws_iam as iam,
    aws_rds as rds,
    aws_ec2 as ec2,
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
            peer=ec2.Peer.ipv4("10.0.0.0/16"),
            connection=ec2.Port.tcp(int(constants.get('BACKEND_PORT')))
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
        