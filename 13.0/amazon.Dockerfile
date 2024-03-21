# https://docs.aws.amazon.com/efs/latest/ug/installing-amazon-efs-utils.html

# Build amazon-efs-utils package.
FROM debian:buster-slim
RUN apt-get update && apt-get -y install git binutils
RUN git clone https://github.com/aws/efs-utils /usr/local/src/efs-utils
RUN cd /usr/local/src/efs-utils && ./build-deb.sh

# Install amazon-efs-utils and python3-boto3 packages.
FROM odoo:13
USER root
COPY --from=0 /usr/local/src/efs-utils/build/*.deb /tmp
RUN apt-get update && apt-get install -y python3-boto3 /tmp/amazon-efs-utils*.deb && rm -rf /var/lib/apt/lists/* /tmp/*.deb
USER odoo
