#!/bin/sh

set -eu

OWNER=${OWNER:-Blira}
REPO=${REPO:-asus-keylight}
REF=${REF:-main}
INSTALL_DIR=${INSTALL_DIR:-"$HOME/.local/share/asus-keylight"}
ARCHIVE_URL="https://codeload.github.com/$OWNER/$REPO/tar.gz/$REF"

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "error: required command not found: $1" >&2
        exit 1
    }
}

download_file() {
    target=$1
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$ARCHIVE_URL" -o "$target"
        return
    fi
    if command -v wget >/dev/null 2>&1; then
        wget -qO "$target" "$ARCHIVE_URL"
        return
    fi
    echo "error: curl or wget is required" >&2
    exit 1
}

need_cmd tar
need_cmd mktemp
need_cmd rm
need_cmd mv
need_cmd sh

if [ ! -d "$INSTALL_DIR" ]; then
    echo "error: no remote install found at $INSTALL_DIR" >&2
    echo "run install-remote.sh first" >&2
    exit 1
fi

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT INT TERM

archive_path="$tmp_dir/asus-keylight.tar.gz"
download_file "$archive_path"
tar -xzf "$archive_path" -C "$tmp_dir"

src_dir=$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)
if [ -z "$src_dir" ]; then
    echo "error: could not extract repository archive" >&2
    exit 1
fi

rm -rf "$INSTALL_DIR"
mv "$src_dir" "$INSTALL_DIR"

echo "Updating install at $INSTALL_DIR"
(
    cd "$INSTALL_DIR"
    sh ./install.sh
)
