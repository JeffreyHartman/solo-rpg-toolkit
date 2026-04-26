#!/usr/bin/env bash
# Ironsworn character status bar for Claude Code.
# Run from the campaign dir; reads CLAUDE.md → Character.md → prints resource bar.

VAULT_PATH=$(grep 'PLAYER_VAULT_PATH:' ./CLAUDE.md 2>/dev/null | head -1 \
    | sed 's/.*PLAYER_VAULT_PATH: //' | xargs)
[ -z "$VAULT_PATH" ] && exit 0

CHAR_FILE="$VAULT_PATH/Character.md"
[ -f "$CHAR_FILE" ] || exit 0

NAME=$(grep '^# '         "$CHAR_FILE" 2>/dev/null | head -1 | sed 's/^# //')
HEALTH=$(grep '^> Health:'   "$CHAR_FILE" 2>/dev/null | head -1 | sed 's/.*Health: //')
SPIRIT=$(grep '^> Spirit:'   "$CHAR_FILE" 2>/dev/null | head -1 | sed 's/.*Spirit: //')
SUPPLY=$(grep '^> Supply:'   "$CHAR_FILE" 2>/dev/null | head -1 | sed 's/.*Supply: //')
MOMENTUM=$(grep '^> Momentum:' "$CHAR_FILE" 2>/dev/null | grep -v 'bounds' \
    | head -1 | sed 's/.*Momentum: //')

BOLD=$'\033[1m'; RST=$'\033[0m'
GRN=$'\033[32m'; BLU=$'\033[34m'; YLW=$'\033[33m'; MAG=$'\033[35m'; RED=$'\033[31m'

HP_CUR=$(echo "$HEALTH" | cut -d'/' -f1 | tr -d '+')
HP_MAX=$(echo "$HEALTH" | cut -d'/' -f2 | tr -d '+')
HP_COLOR=$GRN
[ -n "$HP_CUR" ] && [ -n "$HP_MAX" ] && \
    [ "$HP_CUR" -le $((HP_MAX / 2)) ] 2>/dev/null && HP_COLOR=$RED

printf "%s%s%s | %sHP:%s%s  %sSP:%s%s  %sSU:%s%s  %sMO:%s%s" \
    "$BOLD" "$NAME" "$RST" \
    "$HP_COLOR" "$HEALTH" "$RST" \
    "$BLU" "$SPIRIT" "$RST" \
    "$YLW" "$SUPPLY" "$RST" \
    "$MAG" "$MOMENTUM" "$RST"
