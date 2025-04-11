#!/bin/bash
set -euo pipefail

########################################################################################
# Usage: ./find_bad_sites.sh /.../jobs/ TASKFORCE_UUID|WORKFLOW_ID "error pattern"
#   Example:
#     ./find_bad_sites.sh /scratch/ewms/tms-foo/jobs TF-abc123-f56 "Segmentation fault"
#     ./find_bad_sites.sh /scratch/ewms/tms-foo/jobs WF-abc123 "Segmentation fault"
########################################################################################

# Validate input arguments
if [[ -z "${1-}" || -z "${2-}" || -z "${3-}" ]]; then
    echo "Usage: $0 TMS_JOBS_DIR TASKFORCE_UUID|WORKFLOW_ID 'error pattern'"
    exit 1
fi

JOBS_DIR="$1"
TF_OR_WF="$2"
ERROR_PATTERN="$3"

# Ensure the given directory ends with /jobs
if [[ ! -d "$JOBS_DIR" || "$(basename "$JOBS_DIR")" != "jobs" ]]; then
    echo "ERROR: $JOBS_DIR is not a '.../jobs/' directory"
    exit 2
fi

########################################################################################
# find cluster dir

# Resolve taskforce from either TF-UUID or WF-ID
if [[ "$TF_OR_WF" =~ ^TF- ]]; then
    # If a taskforce UUID is directly provided
    TASKFORCE_UUID="$TF_OR_WF"
elif [[ "$TF_OR_WF" =~ ^WF- ]]; then
    # If a workflow ID is provided, find all matching taskforces (replace WF- with TF-)
    WORKFLOW_ID="$TF_OR_WF"
    WF_SUFFIX="${TF_OR_WF#WF-}"
    readarray -t TF_MATCHES <<< "$(find "$JOBS_DIR" -maxdepth 1 -type d -name "ewms-taskforce-TF-${WF_SUFFIX}-*" | sort)"

    # If no taskforces found, exit
    if [[ ${#TF_MATCHES[@]} -eq 0 ]]; then
        echo "ERROR: No taskforces found for workflow ID $WORKFLOW_ID"
        exit 3

    # If one taskforce found, use it
    elif [[ ${#TF_MATCHES[@]} -eq 1 ]]; then
        TASKFORCE_UUID=$(basename "${TF_MATCHES[0]}" | sed 's/^ewms-taskforce-//')

    # If multiple taskforces found, prompt the user
    else
        echo "[Prompt] Multiple taskforces found for workflow ID $WORKFLOW_ID:"
        select choice in "${TF_MATCHES[@]}"; do
            [[ -n "$choice" ]] && break
        done
        TASKFORCE_UUID=$(basename "$choice" | sed 's/^ewms-taskforce-//')
    fi
else
    # Invalid ID format
    echo "ERROR: Must start with TF- or WF-"
    exit 1
fi

# Find the cluster directory under the selected taskforce
readarray -t matches <<< "$(find "$JOBS_DIR/ewms-taskforce-$TASKFORCE_UUID" -maxdepth 1 -type d -name 'cluster-*')"

# Must find exactly one cluster directory
if [[ ${#matches[@]} -ne 1 ]]; then
    echo "ERROR: Expected exactly one cluster dir, found ${#matches[@]}"
    exit 2
fi

CLUSTER_DIR="${matches[0]}"
echo "using cluster directory: $CLUSTER_DIR"


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
echo "[Step 3] Comparing matched vs total for site '$SITE' in '$CLUSTER_DIR'"

match_count=$(echo "$MATCHED_LINES" | grep -c "GLIDEIN_Site=$SITE")
total_count=$(grep -r --include='*.out' "GLIDEIN_Site=$SITE" "$CLUSTER_DIR" | wc -l)

echo "  Matched jobs at $SITE: $match_count"
echo "  Total   jobs at $SITE: $total_count"

########################################################################################
# report findings

echo

if [[ "$match_count" -ne "$total_count" ]]; then
  echo "[Info] Not all jobs from '$SITE' matched with '$ERROR_PATTERN'. Not continuing to TMS-wide scan."
  echo "[Done] $SITE is NOT a bad site."
  exit 0
else
  echo "[Info] $SITE is **potentially** a bad site."
fi

########################################################################################
# see if this site always fails with this error (all clusters)

echo
echo "[Step 4] Checking all jobs in '$TMS_JOBS_DIR' for '$SITE' with '$ERROR_PATTERN'..."

all_match_count=$(grep -rl --include='*.err' "$ERROR_PATTERN" "$TMS_JOBS_DIR" | \
  awk -F '.err' '{print $1".out"}' | \
  xargs -r grep "GLIDEIN_Site=$SITE" | wc -l)

all_total_count=$(grep -r --include='*.out' "GLIDEIN_Site=$SITE" "$TMS_JOBS_DIR" | wc -l)

echo "  Total matched across all clusters: $all_match_count"
echo "  Total jobs    across all clusters: $all_total_count"

########################################################################################
# report findings

echo

if [[ "$all_match_count" -eq "$all_total_count" ]]; then
  echo "[Info] All jobs matched with '$ERROR_PATTERN'"
  echo "[Done] '$SITE' is a bad site!"
else
  echo "[Done] '$SITE' is NOT a bad site."
fi
