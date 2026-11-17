#!/bin/bash
# =============================================================================
# Docker Compose Watchdog Template
# =============================================================================
# Drop this into ~/.hermes/scripts/<stack-name>-watchdog.sh
# Schedule with: cronjob(action='create', name='<name>-watchdog', schedule='every 1m',
#                     script='<name>-watchdog.sh', no_agent=True)
# =============================================================================

COMPOSE_DIR="<%= it.COMPOSE_DIR %>"    # e.g., /home/user/honcho
COMPOSE_FILE="docker-compose.yml"       # or docker-compose.prod.yml, etc.
PROJECT_NAME="<%= it.PROJECT_NAME %>"   # e.g., honcho
EXPECTED_SERVICES="api database worker redis"  # space-separated service names

cd "$COMPOSE_DIR" || { echo "[watchdog] ERROR: cannot cd to $COMPOSE_DIR"; exit 1; }
LOG_TAG="[${PROJECT_NAME}-watchdog]"

# Check unhealthy / exited containers
UNHEALTHY=$(docker compose -f "$COMPOSE_FILE" ps --format '{{.Name}} {{.Status}}' | grep -i 'unhealthy' | awk '{print $1}')
EXITED=$(docker compose -f "$COMPOSE_FILE" ps --format '{{.Name}} {{.Status}}' | grep -i 'exited' | awk '{print $1}')

MESSAGES=""

# Restart unhealthy containers
for c in $UNHEALTHY; do
    echo "$LOG_TAG Restarting unhealthy: $c"
    docker compose -f "$COMPOSE_FILE" up -d --no-deps "${c%%-1}" | tail -1
    MESSAGES="$MESSAGES restarted:$c"
done

# Restart exited containers
for c in $EXITED; do
    echo "$LOG_TAG Restarting exited: $c"
    docker compose -f "$COMPOSE_FILE" up -d --no-deps "${c%%-1}" | tail -1
    MESSAGES="$MESSAGES restarted:$c"
done

# Verify all expected services are running
for svc in $EXPECTED_SERVICES; do
    STATUS=$(docker compose -f "$COMPOSE_FILE" ps --format '{{.Name}} {{.Status}}' | grep "${PROJECT_NAME}-${svc}-1" | head -1)
    if echo "$STATUS" | grep -qiE '(exited|unhealthy)'; then
        MESSAGES="$MESSAGES still-broken:$svc"
    elif [ -z "$STATUS" ]; then
        MESSAGES="$MESSAGES missing:$svc"
    fi
done

# Check CPU impact — warn if consuming >50%
CPU=$(docker compose -f "$COMPOSE_FILE" top 2>/dev/null | grep -v 'UID\|PID' | awk '{sum+=$3} END {print int(sum)}')
if [ -n "$CPU" ] && [ "$CPU" -gt 50 ] 2>/dev/null; then
    MESSAGES="$MESSAGES high-cpu:${CPU}%"
fi

# Output and escalate if problems persist
if [ -n "$MESSAGES" ]; then
    echo "$LOG_TAG $(date '+%Y-%m-%d %H:%M:%S') $MESSAGES"
    if echo "$MESSAGES" | grep -q 'still-broken\|missing'; then
        echo "$LOG_TAG Escalating — full stack restart"
        docker compose -f "$COMPOSE_FILE" down && docker compose -f "$COMPOSE_FILE" up -d | tail -5
    fi
    exit 1
fi

exit 0
