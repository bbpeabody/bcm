# This script expects these environment variables to be set:
# USER=<Your Okta userid>
# VDI=<URL of VDI owned by you>

# Get rid of a metadata warning that delays some yum operations.
echo deltarpm=0 >> /etc/yum.conf

# Create a user on guest for the okta username.  This makes the signing
# script happy because it checks to make sure the user exists on the system.
if ! id -u $USER; then
    adduser -rm $USER
fi

# Install tools required for build
echo "Archiving tools on $VDI (this will take a while)"
# SSH to VDI and tar/gzip the tools required
ssh -o StrictHostKeyChecking=no \
    -i /home/vagrant/.ssh/id_rsa \
    $USER@$VDI 'tar -czf /tmp/tools.tgz /projects/ccxsw_tools/mentor_graphics/mgc-2018.070 /projects/ccxsw_tools/sbl_tools'

# SCP the tools
echo "Copying tools from $VDI (this will take a while)"
scp -o StrictHostKeyChecking=no \
    -i /home/vagrant/.ssh/id_rsa \
    $USER@$VDI:/tmp/tools.tgz /tmp/tools.tgz
# Untar the files
echo "Installing tools (this will take a while)"
cd /
tar -xzf /tmp/tools.tgz
chown --recursive vagrant:vagrant /projects
# Cleanup local
rm /tmp/tools.tgz
# Cleanup remote
ssh -o StrictHostKeyChecking=no \
    -i /home/vagrant/.ssh/id_rsa \
    $USER@$VDI 'rm /tmp/tools.tgz'

#cd /
#tar -xzf /vagrant/mentor_graphics.tgz
#tar -xzf /vagrant/sbl_tools.tgz
#chown --recursive vagrant:vagrant /projects

# Update all packages
yum update -y

# Install newer version of git - v2.16.6.  Centos distro comes with v1.8
yum install -y https://centos7.iuscommunity.org/ius-release.rpm \

# Install packages needed for build
# gcc/++ for building bnxPkgUtil
yum install -y \
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

# Install some optional packages
yum install -y \
    zsh \
    vim

# Upgrade zsh to 5.1, so powerlevel10k theme will work
yum install -y http://mirror.ghettoforge.org/distributions/gf/el/7/plus/x86_64/zsh-5.1-1.gf.el7.x86_64.rpm

yum clean all

# Get powerlevel10k source from github
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git /home/vagrant/powerlevel10k

# Build needs cmake3 but calls cmake
ln -sf /usr/bin/cmake3 /usr/bin/cmake \

# Signing scripts looks for perl in /usr/local/bin
ln -sf /usr/bin/perl /usr/local/bin \

# Set shell to zsh for default vagrant user
usermod --shell /bin/zsh vagrant

# Add USER to .zshrc file.  Signing script uses this variable.
echo export USER=$USER >> /home/vagrant/.zshrc

