#!/usr/bin/env sh
set -eu
curl --fail --silent http://localhost:8000/api/health
printf "\nBackend health check passed.\n"
