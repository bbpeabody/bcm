#!/bin/sh

sessions=("bcm1")
vdi_vegas="bp892475@lvnvda3087.lvn.broadcom.net"
vdi_durham="bp892475@ashvda3390.ash.broadcom.net"
thor_path="/projects/cpxsw_dev/bpeabody/netxtreme/main/Cumulus/firmware/THOR/"
windows=("local1" \
         "local2" \
         "bldr" \
         "vdi-vegas" \
         "vdi-durham" \
         "grinder" \
         "lathe" \
         "tiger")

wait_for_text()
{
    timeout $2 bash <<EOT
    while :; do
        tmux capture-pane -p | grep $1 && break
        sleep 1
    done
EOT
    # Timeout
    return $?
}

tmux start-server
for session in ${sessions[@]}; do
    if tmux list-sessions | grep $session &> /dev/null; then
        echo "Session $session already exists. Skipping" && continue
    fi
    tmux new-session -d -s $session
    # Split windows into 4 quadrants
    # | 0 | 2 |
    # --------
    # | 1 | 3 |
    win_num=0
    for win in ${windows[@]}; do
        echo "Configuring session $session window $win_num($win)..."
        if [ $win_num = 0 ]; then
            tmux rename-window -t $session:$win_num "$win"
        else
            tmux new-window -t $session -n "$win"
        fi
        tmux splitw -h -t 0
        tmux splitw -v -t 1
        tmux splitw -v -t 0
        for pane in {0..3}; do
            tmux selectp -t $pane
            case $win in
                "local1" | "local2")
                    tmux send-keys "cd ~" C-m
                    tmux send-keys "reset" C-m
                    ;;
                "bldr")
                    if docker ps | grep ' bldr' &> /dev/null; then
                        # Container already running, attach another shell
                        tmux send-keys "docker exec -it bldr /bin/bash" C-m
                    elif docker ps -a | grep 'Exited.* bldr' &> /dev/null; then
                        # Container exists but is not running, so remove it and restart
                        tmux send-keys "docker container rm bldr" C-m
                        sleep 2
                        tmux send-keys "cd ~/git/bcm/docker && ./run --name bldr" C-m
                        sleep 5
                    else
                        # Start the container
                        tmux send-keys "cd ~/git/bcm/docker && ./run --name bldr" C-m
                        sleep 5
                    fi
                    tmux send-keys "clear" C-m
                    ;;
                "vdi-vegas" | "vdi-durham")
                    if [ $win = "vdi-vegas" ]; then
                        ssh=$vdi_vegas
                    else
                        ssh=$vdi_durham
                    fi
                    tmux send-keys "ssh $ssh -o 'PermitLocalCommand yes' -o 'LocalCommand tmux wait-for -S cmd-done'" C-m
                    gtimeout 5 tmux wait-for cmd-done || { echo "Timed out waiting for ssh $ssh" && break; }
                    tmux send-keys "cd $thor_path" C-m
                    tmux send-keys "clear" C-m
                    ;;
                #"shaper" | "domino" | "rail" | "stile" | "tiger")
                *)
                    tmux send-keys "ssh $win -o 'PermitLocalCommand yes' -o 'LocalCommand tmux wait-for -S cmd-done'" C-m
                    gtimeout 5 tmux wait-for cmd-done || { echo "Timed out waiting for ssh $win" && break; }
                    ;;
            esac
        done
        let win_num+=1
    done
    tmux select-window -t $session:0
    tmux selectp -t 0
done
