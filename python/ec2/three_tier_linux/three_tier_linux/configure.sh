#!/bin/bash -xe
# Use this file to install software packages
exec > >(tee /var/log/user-data.log) 2>&1
    yum update -y
    yum install -y docker
    systemctl enable docker
    # usermod -a -G docker ec2-user
    systemctl start docker

    # put apache container service in place during development
    # TODO: switch to service that uses RDS database credentials
    # Must pull RDS creds from Secrets Manager
    echo '
[Unit]
Description=Apache Service
After=docker.service
Requires=docker.service
#After=docker.httpd.service
#Requires=docker.httpd.service

[Service]
TimeoutStartSec=0
Restart=always
ExecStartPre=-/usr/bin/docker stop httpd
ExecStartPre=-/usr/bin/docker rm httpd
ExecStartPre=/usr/bin/docker pull httpd:alpine
ExecStart=/usr/bin/docker run --name httpd -p 80:80 --rm httpd:alpine

[Install]
WantedBy=multi-user.target' >/etc/systemd/system/docker.httpd.service
    systemctl enable docker.httpd
    systemctl start docker.httpd
