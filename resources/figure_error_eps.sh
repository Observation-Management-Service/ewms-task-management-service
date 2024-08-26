#!/bin/bash
set -e

########################################################################
#
# Finds which EPs were successful and which were not
#
########################################################################

if [ ! -d "$1" ]; then
    echo "Usage: figure_error_eps.sh LOG_DIRECTORY"
    exit 1
else
    LOG_DIRECTORY="$1"
fi


########################################################################
# get condor history - for attrs not stored in job log

cluster_id=$( echo $LOG_DIRECTORY | sed 's:/*$::' | awk -F"-cluster-" '{print $2}' )
classads_file="cluster-$cluster_id.classads"

if [ -e $classads_file ]; then
    echo "Looking at $classads_file"  1>&2
else
    echo "Looking at condor history for $cluster_id (this will take some time)"  1>&2
    condor_history -long $cluster_id  > $classads_file
fi


########################################################################
# collect

# Loop through all files in the directory
job_procid_array=()  # Initialize an empty array to hold unique stems
for file in $LOG_DIRECTORY/*; do
    # Extract the file stem (everything before the first dot)
    job_procid=$(basename "$file" | cut -d. -f1)

    # Check if the stem is already in the array
    if [[ ! " ${job_procid_array[*]} " =~ " ${job_procid} " ]]; then
        # If not, add it to the array
        job_procid_array+=("$job_procid")
    fi
done


########################################################################
# analyze

successes=()
failures=()

# Loop through the unique job procids
for job_procid in "${job_procid_array[@]}"; do
    # check *.err for "Done." in last line
    if [[ $( tail -n 1 "$LOG_DIRECTORY/$job_procid".err ) != *"Done."* ]]; then
        failures+=("$job_procid")
    else
        successes+=("$job_procid")
    fi
done


########################################################################
# print!
exec > "cluster-$cluster_id.performance"  # change echos to file

echo "============================"
echo "$LOG_DIRECTORY"
echo "-> $( stat -c %y $LOG_DIRECTORY )"

echo
echo "Failed (${#failures[@]}):"
echo "----"
for job_procid in "${failures[@]}"; do
    echo "    #$job_procid:"
    echo "        $( grep "Hostname:" "$LOG_DIRECTORY/$job_procid".out | tr -d "║" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' )"
    echo "        $( grep -B 40 "ProcId = $job_procid" $classads_file | grep "skymap_scanner/client/client.py:92" | tail -1 )"  # want first match above 'ProcId'
    echo "        path: $LOG_DIRECTORY/$job_procid.err"
    echo "        $( tail -n 1  "$LOG_DIRECTORY/$job_procid".err )"
    echo "----"
done

echo
echo "Succeeded (${#successes[@]}):"
echo "----"
for job_procid in "${successes[@]}"; do
    echo "    #$job_procid:"
    echo "        $( grep "Hostname:" "$LOG_DIRECTORY/$job_procid".out | tr -d "║" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' )"
    echo "        $( grep -B 40 "ProcId = $job_procid" $classads_file | grep "LastRemoteHost" | tail -1 )"  # want first match above 'ProcId'
    echo "----"
done

echo
echo "Failed=${#failures[@]} Succeeded=${#successes[@]}"
