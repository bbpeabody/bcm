# Start with Fedora 32
FROM fedora:32 AS base

# Update all packages
RUN yum update -y \
&& yum install -y \
    vim \
    gcc gcc-c++ \
    git \
    python-pip \
    python3 \
    gtk2 \
    alsa-lib \
    mesa-libGLU \
    libusb \
    libXt \
    libXtst \
    libgcc \
    libgcc.i686 \
    libstdc++ \
    libstdc++.i686 \
    zlib \
    zlib.i686 \
    librsvg2 \
    ncurses-devel \
    ncurses \
    ncurses-compat-libs \
    libnsl \
    gtk3 \
    dbus-x11 \
&& yum clean all

ARG user
ARG group
ARG uid
ARG gid
ARG armds_dir
ARG armds_tgz
ARG armds_installer
ARG armds_installdir

# Ensure the user set the required arguments.
RUN args=(user group uid gid armds_dir armds_tgz armds_installer armds_installdir); \
    for arg in ${args[*]}; do \
        if [ -z ${!arg} ]; then \
            echo "$arg must be set as a build argument"; \
            exit 1; \
        fi \
    done

# Delete user if already exists on base Fedora
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

# Set the user and working dir so the container start with them.
# Add any customizations.
WORKDIR /home/$user
COPY .*  ./
RUN chown $user:$group .*

COPY ${armds_tgz} /tmp/
RUN echo /tmp/${armds_tgz}
RUN tar -C /tmp -xf /tmp/${armds_tgz}
RUN /tmp/${armds_dir}/${armds_installer} --i-agree-to-the-contained-eula --no-interactive -d ${armds_installdir}
RUN rm -fr /tmp/${armds_tgz} /tmp/${armds_dir}

# Get the smallest image possible.
FROM scratch
COPY --from=base / /

CMD ["/bin/bash"]
