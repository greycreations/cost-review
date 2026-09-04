#!/bin/sh

set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
example_file="$repository_root/.env.example"
environment_file="$repository_root/.env"

if [ "$#" -gt 1 ]; then
  echo "Usage: ./scripts/init-env.sh [public-url]" >&2
  exit 2
fi

if [ -e "$environment_file" ]; then
  echo "$environment_file already exists; refusing to overwrite it." >&2
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "OpenSSL is required to generate installation secrets." >&2
  exit 1
fi

if [ "$#" -eq 1 ]; then
  public_url=$1
else
  detected_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  default_url="http://${detected_ip:-localhost}:8080"
  printf "Address used to open Cost Review [%s]: " "$default_url"
  read -r public_url || true
  public_url=${public_url:-$default_url}
fi

case "$public_url" in
  http://*|https://*) ;;
  *)
    echo "The address must begin with http:// or https://" >&2
    exit 1
    ;;
esac

authority=${public_url#http://}
authority=${authority#https://}
authority=${authority%%/*}
allowed_host=${authority%%:*}

case "$allowed_host" in
  ""|*[!A-Za-z0-9.-]*)
    echo "Use an IPv4 address or DNS hostname in the public URL." >&2
    exit 1
    ;;
esac

cookie_secure=false
case "$public_url" in
  https://*) cookie_secure=true ;;
esac

prod_password=$(openssl rand -hex 32)
test_password=$(openssl rand -hex 32)
prod_backup_key=$(openssl rand -hex 32)
test_backup_key=$(openssl rand -hex 32)

umask 077
awk \
  -v prod_password="$prod_password" \
  -v test_password="$test_password" \
  -v prod_backup_key="$prod_backup_key" \
  -v test_backup_key="$test_backup_key" \
  -v public_url="$public_url" \
  -v allowed_host="$allowed_host" \
  -v cookie_secure="$cookie_secure" '
    /^POSTGRES_PROD_PASSWORD=/ { print "POSTGRES_PROD_PASSWORD=" prod_password; next }
    /^POSTGRES_TEST_PASSWORD=/ { print "POSTGRES_TEST_PASSWORD=" test_password; next }
    /^BACKUP_PROD_ENCRYPTION_KEY=/ { print "BACKUP_PROD_ENCRYPTION_KEY=" prod_backup_key; next }
    /^BACKUP_TEST_ENCRYPTION_KEY=/ { print "BACKUP_TEST_ENCRYPTION_KEY=" test_backup_key; next }
    /^COOKIE_SECURE=/ { print "COOKIE_SECURE=" cookie_secure; next }
    /^APP_ALLOWED_ORIGINS=/ { print "APP_ALLOWED_ORIGINS=" public_url; next }
    /^APP_ALLOWED_HOSTS=/ { print "APP_ALLOWED_HOSTS=" allowed_host; next }
    { print }
  ' "$example_file" > "$environment_file"

chmod 600 "$environment_file"

echo "Created $environment_file with unique installation secrets."
echo "Configured application address: $public_url"
echo "Next command: docker compose up --detach --wait"
