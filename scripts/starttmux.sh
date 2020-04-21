#!/bin/sh

send () {
    cmd="$1; tmux wait-for -S cmd-done"
    tmux send-keys "$cmd" C-m
    tmux wait-for cmd-done
}

session="bcm"
vdi_vegas="bp892475@lvnvda3087.lvn.broadcom.net"
vdi_durham="bp892475@ashvda3390.ash.broadcom.net"
thor_path="/projects/cpxsw_dev/bpeabody/netxtreme/main/Cumulus/firmware/THOR/"

tmux start-server

tmux new-session -d -s $session

# Window 0 Configuration - 4 quandrants, local machine
# Split first window into 4 quadrants
# | 0 | 2 |
# --------
# | 1 | 3 |
echo "Configuring window 0..."
tmux rename-window -t $session:0 "local"
tmux splitw -h -t 0
tmux splitw -v -t 1
tmux splitw -v -t 0
for i in {0..3}
do
    tmux send-keys -t $i "cdthor" C-m
    tmux send-keys -t $i "reset" C-m
done

# Window 1 Configuration - 4 quandrants, vagrant VM
# Make sure vagrant VM is up
echo "Configuring window 1..."
pushd ~/git/bcm/vagrant &> /dev/null
vagrant status | grep running &> /dev/null || { echo "Starting vagrant VM..." && { vagrant up || echo "ERROR: Failed to start vagrant VM"; } }
popd &> /dev/null
tmux new-window -t $session -n "bldr"
tmux select-window -t $session:1
tmux splitw -h -t 0
tmux splitw -v -t 1
tmux splitw -v -t 0
for i in {0..3}
do
    tmux selectp -t $i
    tmux send-keys "cd ~/git/bcm/vagrant && vagrant ssh -- -Y -o 'PermitLocalCommand yes' -o 'LocalCommand tmux wait-for -S cmd-done'" C-m
    gtimeout 5 tmux wait-for cmd-done || { echo "Timed out waiting for vagrant ssh" && break; }
    tmux send-keys "cdthor" C-m
    tmux send-keys "clear" C-m
done

# Window 2 Configuration - 4 quandrants, Las Vegas VDI
echo "Configuring window 2..."
tmux new-window -t $session -n "vdi-vegas"
tmux select-window -t $session:2
tmux splitw -h -t 0
tmux splitw -v -t 1
tmux splitw -v -t 0
for i in {0..3}
do
    tmux selectp -t $i
    tmux send-keys "ssh $vdi_vegas -o 'PermitLocalCommand yes' -o 'LocalCommand tmux wait-for -S cmd-done'" C-m
    gtimeout 5 tmux wait-for cmd-done || { echo "Timed out waiting for ssh $vdi_vegas" && break; }
    tmux send-keys "cd $thor_path" C-m
    tmux send-keys "clear" C-m
done

# Window 3 Configuration - 4 quandrants, Durham VDI
echo "Configuring window 3..."
tmux new-window -t $session -n "vdi-durham"
tmux select-window -t $session:3
tmux splitw -h -t 0
tmux splitw -v -t 1
tmux splitw -v -t 0
for i in {0..3}
do
    tmux selectp -t $i
    tmux send-keys "ssh $vdi_durham -o 'PermitLocalCommand yes' -o 'LocalCommand tmux wait-for -S cmd-done'" C-m
    gtimeout 5 tmux wait-for cmd-done || { echo "Timed out waiting for ssh $vdi_durham" && break; }
    tmux send-keys "cd $thor_path" C-m
    tmux send-keys "clear" C-m
done

tmux select-window -t $session:0
tmux selectp -t 0

# Window 4 Configuration - 4 quandrants, shaper
echo "Configuring window 4..."
tmux new-window -t $session -n "shaper"
tmux select-window -t $session:4
tmux splitw -h -t 0
tmux splitw -v -t 1
tmux splitw -v -t 0
for i in {0..3}
do
    tmux selectp -t $i
    tmux send-keys "ssh shaper -o 'PermitLocalCommand yes' -o 'LocalCommand tmux wait-for -S cmd-done'" C-m
    gtimeout 5 tmux wait-for cmd-done || { echo "Timed out waiting for ssh shaper" && break; }
done

# Window 5 Configuration - 4 quandrants, domino
echo "Configuring window 5..."
tmux new-window -t $session -n "domino"
tmux select-window -t $session:5
tmux splitw -h -t 0
tmux splitw -v -t 1
tmux splitw -v -t 0
for i in {0..3}
do
    tmux selectp -t $i
    tmux send-keys "ssh domino -o 'PermitLocalCommand yes' -o 'LocalCommand tmux wait-for -S cmd-done'" C-m
    gtimeout 5 tmux wait-for cmd-done || { echo "Timed out waiting for ssh domino" && break; }
done

tmux select-window -t $session:0
tmux selectp -t 0
