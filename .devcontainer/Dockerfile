FROM mcr.microsoft.com/devcontainers/base:ubuntu

# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    # Install postgresql-client for the `psql` command
    postgresql-client

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer for all users then remove it
RUN UV_INSTALL_DIR="/usr/local/bin" sh /uv-installer.sh \
    && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/usr/local/bin:$PATH"