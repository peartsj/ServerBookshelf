#!/bin/sh
set -eu

API_BASE_URL="${FRONTEND_API_BASE_URL:-/api}"

cat > /usr/share/nginx/html/env.js <<EOF
window.__APP_CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL}"
};
EOF
