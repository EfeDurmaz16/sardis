#!/bin/sh
# Sardis CLI installer
# Usage: curl -sSL https://sardis.sh/install.sh | sh
set -e

REPO="sardis-sh/sardis"
BINARY="sardis"
INSTALL_DIR="/usr/local/bin"

# Detect OS and arch
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
  x86_64|amd64) ARCH="amd64" ;;
  arm64|aarch64) ARCH="arm64" ;;
  *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

case "$OS" in
  linux) OS="linux" ;;
  darwin) OS="darwin" ;;
  *) echo "Unsupported OS: $OS"; exit 1 ;;
esac

# Get latest version
VERSION=$(curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name"' | sed 's/.*"v\(.*\)".*/\1/' 2>/dev/null || echo "")

if [ -z "$VERSION" ]; then
  echo "Could not determine latest version. Check https://github.com/${REPO}/releases"
  exit 1
fi

FILENAME="${BINARY}_${OS}_${ARCH}.tar.gz"
URL="https://github.com/${REPO}/releases/download/v${VERSION}/${FILENAME}"

echo "Sardis CLI Installer"
echo "  Version:  v${VERSION}"
echo "  OS:       ${OS}"
echo "  Arch:     ${ARCH}"
echo ""

# Download
TMP_DIR=$(mktemp -d)
echo "Downloading ${URL}..."
curl -sSL "$URL" -o "${TMP_DIR}/${FILENAME}"

# Extract
echo "Extracting..."
tar -xzf "${TMP_DIR}/${FILENAME}" -C "${TMP_DIR}"

# Install
if [ -w "$INSTALL_DIR" ]; then
  mv "${TMP_DIR}/${BINARY}" "${INSTALL_DIR}/${BINARY}"
else
  echo "Installing to ${INSTALL_DIR} (requires sudo)..."
  sudo mv "${TMP_DIR}/${BINARY}" "${INSTALL_DIR}/${BINARY}"
fi

chmod +x "${INSTALL_DIR}/${BINARY}"

# Cleanup
rm -rf "$TMP_DIR"

echo ""
echo "Sardis CLI v${VERSION} installed to ${INSTALL_DIR}/${BINARY}"
echo ""
echo "Get started:"
echo "  sardis login"
echo "  sardis status"
echo "  sardis dashboard"
