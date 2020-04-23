# Start with CentOS7
FROM centos:7 AS base

ARG uservdi
ARG user
ARG group
ARG uid
ARG gid

# Ensure the user set the required arguments.
RUN args=(uservdi user group uid gid); \
    for arg in ${args[*]}; do \
        if [ -z ${!arg} ]; then \
            echo "$arg must be set as a build argument"; \
            exit 1; \
        fi \
    done

# Update all packages
RUN yum update -y \
&& yum install -y https://centos7.iuscommunity.org/ius-release.rpm \
&& yum install -y \
    vim \
    cmake3 \
    gcc gcc-c++ \
    git2u \
    glibc.i686 glibc-static \
    java-1.8.0-openjdk-headless \
    kernel-devel \
    make \
    perl-WWW-Mechanize \
    tcl-devel \
    npm \
    python-pip \
    sudo \
    npm \
&& yum clean all

# Build needs cmake3 but calls cmake
RUN ln -sf /usr/bin/cmake3 /usr/bin/cmake

# Signing scripts looks for perl in /usr/local/bin
RUN ln -sf /usr/bin/perl /usr/local/bin

# Try to match up the host user:group with the guest user:group.
# Delete the guest user and group if found, then
# add new user, add to wheel group and update sudoers to allow passwordless sudo
# Add the vdi user. The signing scripts require a user account.
# Only create the vdi account if it is different than user.
RUN if id -u $user; then userdel $user; fi \
    && gname=`getent group $gid | cut -d':' -f 1` && echo "looking for group($gid): $gname" \
    && if [ -n "$gname" ]; then groupdel $gname; fi \
    && groupadd -g $gid $group \
    && useradd -rm -d /home/$user -u $uid -g $gid -s /bin/bash $user \
    && usermod -aG wheel $user \
    && sed --in-place 's/^#\s*\(%wheel\s\+ALL=(ALL)\s\+NOPASSWD:\s\+ALL\)/\1/' /etc/sudoers \
    && if [ "$user" != "$uservdi" ]; then useradd -rm ${uservdi}; fi

# Set the user and working dir so the container start with them.
# Add any customizations.
WORKDIR /home/$user
COPY .*  ./
RUN chown $user:$group .*

# Update environment
COPY env /tmp/env
RUN cat /tmp/env >> /etc/profile.d/env.sh && rm /tmp/env

# Get the smallest image possible.
FROM scratch
COPY --from=base / /

CMD ["/bin/bash"]
