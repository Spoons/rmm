# bash completion for cryptsetup                           -*- shell-script -*-
#
_rmm()
{
    local cur prev words cword split
    _init_completion -s || return

    local commands='export import list migrate query remove search sync update'
    local singletons='-h --help -v --version'
    local options='-p --path -w --workshop'
    local commands_with_file='export import'

    # $split && return

    for n in $singletons; do
        if [ $prev == $n ]; then
            return
        fi
    done


    if ((cword == 1)); then
        if [[ $cur == -* ]]; then
            COMPREPLY=($(compgen -W "$singletons" -- "$cur"))
        else
            COMPREPLY=($(compgen -W "$commands" -- "$cur"))
        fi
    else
        if [[ $prev == "search" ]]; then
           return
        fi
        if [[ $cur == -* ]]; then
            local used_path=0 used_workshop=0
            local word
            for word in ${words[@]}; do
                case ${word} in
                -p | --path) used_path=1;;
                -w|--workshop) used_workshop=1;;
                esac
            done

            local args
            [ ${used_path} -eq 0 ] && args="-p --path"
            [ ${used_workshop} -eq 0 ] && args="${args} -w --workshop"
            COMPREPLY=($(compgen -W '${args}' -- "$cur"))
        fi

        for n in $options; do
            if [ $prev == $n ]; then
                _filedir -d
            fi
        done

        for n in $commands_with_file; do
            if [[ ${words[1]} == $n ]]; then
                case $cword in
                2 | 5 | 7) _filedir ;;
                esac
            fi
        done
    fi


} &&
    complete -F _rmm rmm

# ex: filetype=sh
