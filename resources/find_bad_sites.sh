#!/bin/bash
set -euo pipefail

########################################################################################
# Usage: ./find_bad_sites.sh /scratch/ewms/tms/tms_scratchdir/ewms-taskforce-TF-[...]/cluster-[...]/ "error pattern"
########################################################################################

if [[ -z "${1-}" || -z "${2-}" ]]; then
  echo "Usage: $0 CLUSTER_DIR 'error pattern'"
  exit 1
fi

CLUSTER_DIR="$1"
ERROR_PATTERN="$2"
ROOT_DIR="/scratch/ewms/tms/tms_scratchdir"

########################################################################################
# find all sites in cluster

echo "[Step 1] Finding .err files with '$ERROR_PATTERN' in cluster dir: $CLUSTER_DIR"

echo && set -x
MATCHED_LINES=$(grep -rl --include='*.err' "$ERROR_PATTERN" "$CLUSTER_DIR" | \
  awk -F '.err' '{print $1".out"}' | \
  xargs -r grep 'GLIDEIN_Site=')
set +x

########################################################################################
# ask user for site

echo
echo "[Step 2] Sites seen with '$ERROR_PATTERN':"
echo "$MATCHED_LINES" | cut -d: -f2-

echo
read -rp "Which site would you like to check? " SITE

########################################################################################
# see if this site always fails with this error (this cluster)

echo
echo "[Step 3] Comparing matched vs total for site '$SITE' in cluster dir..."

match_count=$(echo "$MATCHED_LINES" | grep -c "GLIDEIN_Site=$SITE")
total_count=$(grep -r --include='*.out' "GLIDEIN_Site=$SITE" "$CLUSTER_DIR" | wc -l)

echo "  Matched jobs at $SITE: $match_count"
echo "  Total   jobs at $SITE: $total_count"

########################################################################################
# report findings

echo

if [[ "$match_count" -ne "$total_count" ]]; then
  echo "[Info] Not all jobs from $SITE matched with '$ERROR_PATTERN'. Not continuing to global scan."
  echo "[Done] $SITE is NOT a bad site."
  exit 0
else
  echo "[Info] $SITE is **potentially** a bad site."
fi

########################################################################################
# see if this site always fails with this error (all clusters)

echo
echo "[Step 4] Checking all jobs in $ROOT_DIR for $SITE with '$ERROR_PATTERN'..."

all_match_count=$(grep -rl --include='*.err' "$ERROR_PATTERN" "$ROOT_DIR" | \
  awk -F '.err' '{print $1".out"}' | \
  xargs -r grep "GLIDEIN_Site=$SITE" | wc -l)

all_total_count=$(grep -r --include='*.out' "GLIDEIN_Site=$SITE" "$ROOT_DIR" | wc -l)

echo "  Total matched across all clusters: $all_match_count"
echo "  Total jobs    across all clusters: $all_total_count"

########################################################################################
# report findings

echo

if [[ "$all_match_count" -eq "$all_total_count" ]]; then
  echo "[Info] All jobs matched with '$ERROR_PATTERN'"
  echo "[Done] $SITE is a bad site!"
else
  echo "[Done] $SITE is NOT a bad site."
fi
