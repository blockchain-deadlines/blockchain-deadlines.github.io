FROM ubuntu:24.04

# uv for Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
ENV UV_LINK_MODE=copy

# Update, upgrade, and install development tools
RUN apt-get update
RUN apt-get dist-upgrade -y
RUN apt-get autoremove -y --purge
RUN apt-get install -y sudo openssh-client zsh git
RUN apt-get install -y curl wget file
RUN apt-get install -y python3-dev build-essential git-delta nano ripgrep

# Use the non-root user provided by the base image (Claude Code refuses bypassPermissions as root)
RUN echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/ubuntu
RUN usermod -s /usr/bin/zsh ubuntu
RUN curl -sS https://starship.rs/install.sh | sh -s -- --yes

USER ubuntu
