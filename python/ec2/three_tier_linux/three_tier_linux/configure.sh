#!/bin/sh
# Use this to install software packages
yum update -y
yum install -y httpd
systemctl enable httpd
systemctl start httpd
sleep 5
echo '<html><head>Hello from '"${HOSTNAME}"'!!!</head><body></body></html>' >/var/www/html/index.html
