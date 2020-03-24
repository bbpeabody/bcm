# Creating a local VM build machine for Thor
## References
* [CCX Firmware Team OnBoarding](https://docs.google.com/document/d/15jdL361R0cant69XORYLjb7aG75idEfXBIMwFsX2o3M/edit#heading=h.3ndlkh5q3sci)
* [Engineering Virtual Desktop Instance (VDI)](https://sites.google.com/a/broadcom.com/i-t-global-rnd-services/home/unix/vdi)
* [Linux (VDI) Build Process](https://docs.google.com/document/d/1oI2yavh8tIoeKwNg7VZOemNTiE7XfOW6zvX8ploBBOU/edit#heading=h.9c19pik1d7ya)
* [Git-Gerrit Tutorial](http://confluence.broadcom.com/pages/viewpage.action?spaceKey=CCXSW&title=Git-Gerrit+Tutorial)
* [Local Builds](https://docs.google.com/document/d/1ZbmxJGbDqog0OkuCPEiXdKKLtJC6OIJlmzclZP1GqVU/edit#heading=h.h9x9x4f473xn)

## Prerequisites
1. MacOS host.  With some modification to the `Vagrantfile`, this procedure could be adapted to Windows. I've only tested it on MacOS.
1. Install [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
1. Install [Vagrant](https://www.vagrantup.com/downloads.html)
1. Install Vagrant VirtualBox Guest Additions plugin from shell
   ```
   vagrant plugin install vagrant-vbguest
   ```
1. Access to Broadcom Git/Gerrit.  Generate SSH key pair and submit public key to Git/Gerrit admin. See instructions [here](http://confluence.broadcom.com/pages/viewpage.action?spaceKey=CCXSW&title=Git-Gerrit+Tutorial#Git-GerritTutorial-GettingAccess).
1. SSH key pair
   If you followed the Git/Gerrit guide above, you should have used this command on your Mac -
   ```
   ssh-keygen -t rsa -m PEM
   ```
   Your private key should be named `~/.ssh/id_rsa`. This key will be used for git, gerrit, and VDI.
1. A working VDI (Engineering Virtual Desktop Instance). The vagrant `bootstrap.sh` script will use your VDI to retrieve required build tools.  Make sure you can build the firmware on your VDI before attempting to create VM.
   * [Requesting UNIX account](https://broadcomprd.service-now.com/sp?id=sc_cat_item&sys_id=ab444dcd2b61b500391636a3e4da15bc&sysparm_category=e255226f13da9f40551ed2f18144b079)
     * Engineering Domain = Durham
     * Site Code = AM-USA-VA-Ashburn-CoLo(ASH)
   * [VDI Control](https://unixrnd.sjs.avagotech.net/tools/vdi/request.php)
1. Passwordless access to your VDI from host. Once you have your SSH key pair, copy public key to VDI -
   ```
   ssh-copy-id <okta_user>@<vdi_url>
   ```
   Example:  `ssh-copy-id bp892475@lvnvda3087.lvn.broadcom.net`
   The vagrant `bootstrap.sh` script needs passwordless access to your VDI so it can retrieve build tools.
1. SRT/CRT CRID 1 signing priveleges
   Send email to alex.barba@broadcom.com to request signing priveleges for THOR-SD-BROADCOM-CID-0x60000001-SRT (+CRT).  CC your manager for approval.
   
## Instructions
1. Satisfy all prerequistes above
1. Create global `.gitconfig`.  At a minimum, your `.gitconfig` should have your name and Broadcom email address. This will create `~/.gitconfig`.  This file will be copied to the new Vagrant VM when it is brought up for the first time.
   * Show global `.gitconfig`
   ```
   ❯ git config --global --list
   user.name=Brad Peabody
   user.email=brad.peabody@broadcom.com
   color.diff=true
   color.status=true
   color.branch=true
   color.ui=true
   color.editor=vim1. Clone the netxtreme repo to your home directory on the host
   ```
   * Add name to global `.gitconfig`
   ```
   ❯ git config --global user.name "Brad Peabody"
   ```
   * Add email to global `.gitconfig`
   ```
   ❯ git config --global user.email brad.peabody@broadcom.com
   ```
1. Clone `netxtreme` repo
   ```
   mkdir ~/git
   cd ~/git
   git clone svcccxswgit@git-ccxsw.irv.broadcom.com:netxtreme
   cd netxtreme
   git checkout int_nxt
   ```
1. Clone bpeabody's bcm repo from github
   ```
   cd ~/git
   git clone https://github.com/bbpeabody/bcm.git
   ```
1. Change the constants USER and VDI to your Okta userid and VDI URL in `~/git/bcm/vagrant/Vagrantfile`. Example -
   ```
   # Set these to your username and VDI URL
   USER = "bp892475"
   VDI = "lvnvda3087.lvn.broadcom.net"
   ```
1. Bring up the Vagrant VM. This will take a while the first time. Subsequent `vagrant up` commands will be quick. The first time this command is run:
   * Machine is created in VirtualBox
   * CentOS7 is installed
   * Packages are updated and new packages installed
   * Broadcom tools are copied from VDI to the new machine
   ```
   cd ~/git/bcm/vagrant
   vagrant up
   ```
1. Connect to the new Vagrant VM
   ```
   cd ~/git/bcm/vagrant
   vagrant ssh
   ```
1. Once connected to the new VM, you need to create `~/sign.txt`.  This file will contain your password for signing images and is required for the alias `tbuild`.  A function, `mk_sign` is defined in `~/.zshrc`.
   ```
   mk_sign <password>
   ```
1. Build THOR. Aliases used below are defined in ~/.zshrc.
   ```
   cdthor
   tcleanall
   tbuild
   ```
1. Useful vagrant commands
   ```
   vagrant --help
   vagrant up
   vagrant reload (reboots the machine)
   vagrant destroy (Warning: this deletes the machine and everything on it)
   vagrant halt
   vagrant suspend
   vagrant resume
   vagrant ssh
   ```
