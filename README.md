# Creating a local VM build machine for Thor
## Prerequisites
1. MacOS host
2. Install VirtualBox from web
3. Install Vagrant from web
4. Install Vagrant VirtualBox Guest Additions plugin -
   ```
   vagrant plugin install vagrant-vbguest
   ```
5. Access to Broadcom Git/Gerrit. See instructions here -
   http://confluence.broadcom.com/pages/viewpage.action?spaceKey=CCXSW&title=Git-GerritTutorial#Git-GerritTutorial-GettingAccess
6. SSH key pair
   If you followed the Git/Gerrit guide above, you should have used this command on your Mac -
   ```
   ssh-keygen -t rsa -m PEM
   ```
   Your private key should be name ~/.ssh/id_rsa. This key will be used for git, gerrit, and VDI.
7. A working VDI (Engineering Virtual Desktop Instance).
   Bootstrap script will use your VDI to retrieve required build tools.  Make sure you can build the firmware on your VDI before attempting to create VM.
   VDI Request Portal -
   https://unixrnd.sjs.avagotech.net/tools/vdi/request.php
8. Passwordless access to your VDI.
   Once you have your SSH key pair, use this to copy public key to VDI -
   ```
   ssh-copy-id <okta_user>@<vdi_url>
   ```
   Example:  ssh-copy-id bp892475@lvnvda3087.lvn.broadcom.net
   The vagrant bootstrap script needs passwordless access to your VDI so it can retrieve build tools.
9. SRT/CRT CRID 1 signing priveleges
   Send email to alex.barba@broadcom.com to request signing priveleges for THOR-SD-BROADCOM-CID-0x60000001-SRT (+CRT).  CC your manager for approval.
   
## Instructions
1. Satisfy all prerequistes above
2. Create local .gitconfig
3. Clone the netxtreme repo to your home directory on the host
   ```
   mkdir ~/git
   cd ~/git
   git clone svcccxswgit@git-ccxsw.irv.broadcom.com:netxtreme
   cd netxtreme
   git checkout int_nxt
5. Set gerrit as the upstream origin for pushes
6. Change the constants USER and VDI to your Okta userid and VDI URL in vagrant/Vagrantfile
