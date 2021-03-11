#!/bin/bash -xe

APP_NAME='three-tier-linux'
DEPLOYMENT_REGION='us-west-2'

# Use this file to install software packages
exec > >(tee /var/log/user-data.log) 2>&1
    yum update -y
    yum install -y docker jq
    systemctl enable docker
    # usermod -a -G docker ec2-user
    systemctl start docker
    sleep 10

    db_secret_name=$(aws --region ${DEPLOYMENT_REGION} ssm get-parameters --names "/${APP_NAME}/db_secret" --query 'Parameters[0].Value' --output text)
    db_secret_value=$(aws --region ${DEPLOYMENT_REGION} secretsmanager get-secret-value --secret-id ${db_secret_name} --query 'SecretString' --output text)

    # Test wordpress service with connection to RDS DB
    docker pull wordpress
    docker_command='/usr/bin/docker run --name wordpress -p 80:80 --rm'
    docker_command="${docker_command} -e WORDPRESS_DB_HOST=$(echo $db_secret_value|jq .host|sed 's/"//g')" # :$(echo $db_secret_value |jq .port)"
    docker_command="${docker_command} -e WORDPRESS_DB_USER=$(echo $db_secret_value |jq .username|sed 's/"//g')"
    docker_command="${docker_command} -e WORDPRESS_DB_PASSWORD=$(echo $db_secret_value |jq .password|sed 's/"//g')"
    docker_command="${docker_command} -e WORDPRESS_DB_NAME=$(echo ${APP_NAME}| sed 's/-//g')"
    docker_command="${docker_command} -e WORDPRESS_DEBUG=1 -v /var/www/html:/var/www/html wordpress"
    echo '
[Unit]
Description=Wordpress Service
After=docker.service
Requires=docker.service
#After=docker.wordpress.service
#Requires=docker.wordpress.service

[Service]
TimeoutStartSec=0
Restart=always
ExecStartPre=-/usr/bin/docker stop wordpress
ExecStartPre=-/usr/bin/docker rm wordpress
ExecStartPre=/usr/bin/docker pull wordpress
ExecStart='"${docker_command}"'

[Install]
WantedBy=multi-user.target' >/etc/systemd/system/docker.wordpress.service
    systemctl enable docker.wordpress
    systemctl start docker.wordpress
