# This script expects these environment variables to be set:
# USER=<Your Okta userid>
# VDI=<URL of VDI owned by you>

# Get rid of a metadata warning that delays some yum operations.
echo deltarpm=0 >> /etc/yum.conf

# Create a user on guest for the okta username.  This makes the signing
# script happy because it checks to make sure the user exists on the system.
echo "Creating user $USER"
if ! id -u $USER; then
    adduser -rm $USER
fi

# Install tools required for build
echo "Archiving tools on $VDI (this will take a while)"
# SSH to VDI and tar/gzip the tools required
ssh -o StrictHostKeyChecking=no \
    -i /home/vagrant/.ssh/id_rsa \
    $USER@$VDI \
    'tar -czf /tmp/tools.tgz \
        /projects/ccxsw_tools/mentor_graphics/mgc-2018.070 \
        /projects/ccxsw_tools/sbl_tools \
        /projects/ccxsw_tools/contrib \
        /projects/ccxsw_tools/coverity/2019.03/Linux-64 \
	/projects/ccxsw_tools/coverity/cov-analysis-linux64-2019.03'

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

# Update all packages
echo "Updating all packages"
yum update -y

# Install newer version of git - v2.16.6.  Centos distro comes with v1.8
echo "Installing newer version of git"
yum install -y https://centos7.iuscommunity.org/ius-release.rpm \

# Install additional packages
# gcc/++ for building bnxPkgUtil
echo "Installing new packages"
yum install -y \
    zsh \
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
    firefox

yum clean all

# Build needs cmake3 but calls cmake
echo "Linking /usr/vin/cmake3 to /usr/bin/cmake"
ln -sf /usr/bin/cmake3 /usr/bin/cmake \

# Signing scripts looks for perl in /usr/local/bin
echo "Linking /usr/bin/perl ==> /usr/local/bin"
ln -sf /usr/bin/perl /usr/local/bin \

# Set netxtreme repo push origin to Gerrit and install client side git hooks
echo "Initializing /git/netxtreme repo (push to Gerrit, client hooks)"
cd /git/netxtreme
runuser -l vagrant -c '/projects/ccxsw_tools/contrib/git/ccxswinit.pl'

# zsh is used by default.  If you want to stick with bash, comment out these commands.
# You'll need to build your own .bashrc
# Upgrade zsh to 5.1, so powerlevel10k theme will work
echo "Upgrading zsh and installing Powerlevel10k theme"
yum install -y http://mirror.ghettoforge.org/distributions/gf/el/7/plus/x86_64/zsh-5.1-1.gf.el7.x86_64.rpm
# Set shell to zsh for default vagrant user
usermod --shell /bin/zsh vagrant
# Get powerlevel10k source from github
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git /home/vagrant/powerlevel10k

# Add USER to .zshenv file.  Signing script uses this variable.
echo "Adding USER=$USER to .zshenv"
echo export USER=$USER >> /home/vagrant/.zshenv

echo "Bootstrap Complete!"
