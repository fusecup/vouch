export LANG='en_US.UTF-8'
export LANGUAGE='en_US:en'
export LC_ALL='en_US.UTF-8'
export TERM=xterm

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
    source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Source Antigen
source ~/.antigen/antigen.zsh
autoload -U colors && colors
setopt promptsubst

# Set up oh-my-zsh
antigen use oh-my-zsh

# Set up plugins
antigen bundle git
antigen bundle docker
antigen bundle zsh-users/zsh-autosuggestions
antigen bundle zsh-users/zsh-syntax-highlighting
antigen bundle zsh-users/zsh-completions
antigen bundle ~/ remy.zsh-theme --no-local-clone

# Run all that config
antigen apply

bindkey "\$terminfo[kcuu1]" history-substring-search-up
bindkey "\$terminfo[kcud1]" history-substring-search-down

alias rmpyc="find . -name '*.pyc' -delete && find . -name '__pycache__' -delete"

alias trans="python manage.py makemessages -l en_GB"

alias compile="python manage.py compilemessages -l en_GB -l de"

alias shell="python manage.py shell_plus --ipython"

alias startapp="f(){ cd fusecup/apps && python ../../manage.py startapp \$@ && cd ../..;  unset -f f; }; f"

alias outdated="uv pip list --outdated"

alias addcomponent="f(){ cd /code/src/fusecup && shadcn_django add \$1 && mv /code/src/fusecup/templates/cotton/\$1 /code/src/fusecup/templates/cotton/uikit/\$1 && cd ..; unset -f f; }; f"