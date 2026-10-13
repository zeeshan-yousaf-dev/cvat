#!/usr/bin/env bash
# Item 5: the stats endpoint for an anonymous caller, a logged-in user with no
# access to the task, and the task owner.
#   bash check_access.sh TASK_ID ADMIN_USER ADMIN_PASSWORD
set -u
HOST=${HOST:-http://localhost:8080}
TASK=$1 ADMIN=$2 ADMIN_PASSWORD=$3
OUTSIDER=outsider OUTSIDER_PASSWORD='Outsider-pass-123'
URL="$HOST/api/annotation-stats/tasks/$TASK"
JAR=$(mktemp -d)

login() { # cookie-jar user password
    curl -s -o /dev/null -c "$1" -H 'Content-Type: application/json' \
        -d "{\"username\":\"$2\",\"password\":\"$3\"}" "$HOST/api/auth/login"
}

curl -s -o /dev/null -H 'Content-Type: application/json' \
    -d "{\"username\":\"$OUTSIDER\",\"email\":\"$OUTSIDER@example.com\",\"password1\":\"$OUTSIDER_PASSWORD\",\"password2\":\"$OUTSIDER_PASSWORD\"}" \
    "$HOST/api/auth/register"
login "$JAR/outsider" "$OUTSIDER" "$OUTSIDER_PASSWORD"
login "$JAR/admin" "$ADMIN" "$ADMIN_PASSWORD"

echo "== anonymous";        curl -s -w '\nHTTP %{http_code}\n' "$URL"
echo "== $OUTSIDER (no access)"; curl -s -w '\nHTTP %{http_code}\n' -b "$JAR/outsider" "$URL"
echo "== $ADMIN (owner)";   curl -s -o /dev/null -w 'HTTP %{http_code}\n' -b "$JAR/admin" "$URL"
rm -r "$JAR"
