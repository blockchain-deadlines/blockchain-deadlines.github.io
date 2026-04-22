# TAB COMPLETION

autoload -Uz compinit && compinit


# HISTORY

HISTFILE="$HOME/.zsh_history"
HISTSIZE=1000000
SAVEHIST=1000000000

setopt APPEND_HISTORY           # append rather than overwrite $HISTFILE
setopt INC_APPEND_HISTORY_TIME  # write each command (with timestamp) as it finishes
setopt EXTENDED_HISTORY         # store start time + duration for each command

setopt SHARE_HISTORY            # (optional) merge history across all sessions

# setopt HIST_EXPIRE_DUPS_FIRST   # when trimming, drop older dups first
# setopt HIST_REDUCE_BLANKS       # collapse extra spaces
# setopt HIST_IGNORE_SPACE        # commands starting with a space aren't saved


# PATHS

export PATH="$HOME/.local/bin:$PATH"


# DEFAULT COMMANDS

export LESS="-R"
export VISUAL="nano"


# ALIASES

alias gits="git status --short"
alias gitd="git diff"
alias gitpp="git pull --no-edit && git push"
alias gitsuper="git add . && git commit -m '.' && git pull --no-edit && git push && git diff HEAD~1"
alias gitc="git commit -m '.'"

alias ll="ls -lAh --color=auto"

alias egrep="egrep --color=auto"

alias de="devcontainer exec --workspace-folder \$(pwd)"


# MORE TAB COMPLETION ?

fpath+=~/.zfunc; autoload -Uz compinit; compinit

zstyle ':completion:*' menu select


# STARSHIP

eval "$(starship init zsh)"
