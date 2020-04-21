
# Start with CentOS7
FROM centos:7

# This script expects these environment variables to be set:
# USER=<Your Okta userid>
# VDI=<URL of VDI owned by you>

ENV USER bp892475
ENV VDI ashvda3390.ash.broadcom.net

# Get rid of a metadata warning that delays some yum operations.
RUN echo deltarpm=0 >> /etc/yum.conf

# Create a user on guest for the okta username.  This makes the signing
# script happy because it checks to make sure the user exists on the system.
RUN adduser -rm $USER

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
    sudo \
    tcl-devel \
    npm \
    python-pip \
    xauth \
    firefox \
    ssh \
&& yum clean all

# Build needs cmake3 but calls cmake
RUN ln -sf /usr/bin/cmake3 /usr/bin/cmake

# Signing scripts looks for perl in /usr/local/bin
RUN ln -sf /usr/bin/perl /usr/local/bin

# Authorize SSH Hosts
RUN mkdir -p /root/.ssh && \
    chmod 0700 /root/.ssh && \
    ssh-keyscan $VDI > /root/.ssh/known_hosts

# Add SSH key
COPY id_rsa /root/.ssh/id_rsa
RUN chmod 0600 /root/.ssh/id_rsa

# Install tools required for build
# SSH to VDI and tar/gzip the tools required
RUN ssh -i /root/.ssh/id_rsa \
    $USER@$VDI \
    'rm -f /tmp/tools.tgz && \
     tar -czvf /tmp/tools.tgz \
              /projects/ccxsw_tools/mentor_graphics/mgc-2018.070 \
              /projects/ccxsw_tools/sbl_tools \
              /projects/ccxsw_tools/contrib \
	          /projects/ccxsw_tools/coverity/2019.03/Linux-64 \
	          /projects/ccxsw_tools/coverity/2019.03/cov-analysis-linux64-2019.03'

# SCP the tools
RUN scp -i /root/.ssh/id_rsa \
    $USER@$VDI:/tmp/tools.tgz /tmp/tools.tgz

# Untar the files and clean-up
RUN cd / && \
    tar -xzf /tmp/tools.tgz && \
    rm /tmp/tools.tgz

# Clean up remote
RUN ssh -i /root/.ssh/id_rsa \
    $USER@$VDI 'rm /tmp/tools.tgz'

# Update environment
COPY env /tmp/env
RUN cat /tmp/env >> /etc/profile.d/env.sh && rm /tmp/env

# Set netxtreme repo push origin to Gerrit and install client side git hooks
#echo "Initializing /git/netxtreme repo (push to Gerrit, client hooks)"
#cd /git/netxtreme
#runuser -l vagrant -c '/projects/ccxsw_tools/contrib/git/ccxswinit.pl'

# zsh is used by default.  If you want to stick with bash, comment out these commands.
# You'll need to build your own .bashrc
# Upgrade zsh to 5.1, so powerlevel10k theme will work
#echo "Upgrading zsh and installing Powerlevel10k theme"
RUN yum install -y http://mirror.ghettoforge.org/distributions/gf/el/7/plus/x86_64/zsh-5.1-1.gf.el7.x86_64.rpm
# Set shell to zsh for root user
RUN usermod --shell /bin/zsh root
# Get powerlevel10k source from github
RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git /usr/local/opt/powerlevel10k

# Add USER to .zshenv file.  Signing script uses this variable.
#echo "Adding USER=$USER to .zshenv"
#echo export USER=$USER >> /home/vagrant/.zshenv

#echo "Bootstrap Complete!"

ENTRYPOINT /usr/bin/zsh
