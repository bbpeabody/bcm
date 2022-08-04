# Start with CentOS7
FROM centos:7 AS base

# Update all packages
RUN yum install -y centos-release-scl
RUN yum update -y \
&& yum install -y https://repo.ius.io/ius-release-el7.rpm \
&& yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm \
&& yum install -y \
    vim \
    cmake3 \
    gcc gcc-c++ \
    git224-all \
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
    python3 \
    gtk2 \
    alsa-lib \
    mesa-libGLU \
    libusb \
    libXt \
    libXtst \
    libgcc \
    #libgcc.i686 \
    libstdc++ \
    #libstdc++.i686 \
    #zlib \
    #zlib.i686 \
    #webkitgtk3 \
    wget \
    scl-utils \
    devtoolset-7 \
    elfutils-libelf-devel \
    doxygen \
    lcov \
&& yum clean all

# Build needs cmake3 but calls cmake
RUN ln -sf /usr/bin/cmake3 /usr/bin/cmake

# Signing scripts looks for perl in /usr/local/bin
RUN ln -sf /usr/bin/perl /usr/local/bin

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

# Delete user if already exists on base CentOS
RUN if id -u $user; then userdel $user; fi

# Delete group if already exists on base CentOS
RUN gname=`getent group $gid | cut -d':' -f 1` && echo "looking for group($gid): $gname" \
    && if [ -n "$gname" ]; then groupdel $gname; fi

# Create new user/group with same user ID/group ID as on host
RUN groupadd -g $gid $group \
    && useradd -rm -d /home/$user -u $uid -g $gid -s /bin/bash $user

# Set owner/group for home dir
RUN chown $user:$group /home/$user

# Add user to sudoers group
RUN usermod -aG wheel $user \
    && sed --in-place 's/^#\s*\(%wheel\s\+ALL=(ALL)\s\+NOPASSWD:\s\+ALL\)/\1/' /etc/sudoers

# Create the VDI user if different from the user.  VDI user is necessary for signing scripts
RUN if [ "$user" != "$uservdi" ]; then useradd -rm ${uservdi}; fi

# Set the user and working dir so the container start with them.
# Add any customizations.
WORKDIR /home/$user
COPY .*  ./
RUN chown $user:$group .*

# Install kernel header files required for bnxtmt build 
COPY kernel-devel-3.10.0-957.27.2.el7.x86_64.rpm ./
RUN rpm -i --force kernel-devel-3.10.0-957.27.2.el7.x86_64.rpm
COPY linux-4.6.tar.gz ./
RUN tar -C /usr/src/kernels -xf linux-4.6.tar.gz 
#COPY kernel-devel-4.18.0-348.el8.x86_64.rpm ./
#RUN rpm -i --force kernel-devel-4.18.0-348.el8.x86_64.rpm
#RUN ln -s /usr/src/kernels/4.18.0-348.el8.x86_64/ /usr/src/kernels/linux-4.6

# Create a link to the ccxsw_tools.  Make expects them to be in /projects
RUN mkdir /projects \
    && ln -s /mnt/build_tools/vdi/ccxsw_tools /projects/ccxsw_tools 

# Get the smallest image possible.
FROM scratch
COPY --from=base / /

CMD ["/bin/bash"]
