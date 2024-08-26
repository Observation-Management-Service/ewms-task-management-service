<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/Observation-Management-Service/ewms-task-management-service?include_prereleases)](https://github.com/Observation-Management-Service/ewms-task-management-service/) [![Lines of code](https://img.shields.io/tokei/lines/github/Observation-Management-Service/ewms-task-management-service)](https://github.com/Observation-Management-Service/ewms-task-management-service/) [![GitHub issues](https://img.shields.io/github/issues/Observation-Management-Service/ewms-task-management-service)](https://github.com/Observation-Management-Service/ewms-task-management-service/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/Observation-Management-Service/ewms-task-management-service)](https://github.com/Observation-Management-Service/ewms-task-management-service/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen)
<!--- End of README Badges (automated) --->

# ewms-task-management-service

A Task Management Service for EWMS

## How to Run

The `image-publish.yml` GitHub Actions workflow publishes this package as an Apptainer image in CVMFS.

Replace the placeholder values, then run this as a one-liner _on sub-2_:

```bash
cd /scratch/$USER && \
    export TMS_WATCHER_INTERVAL=15 && \
    export JOB_EVENT_LOG_DIR="$PWD/tms_scratchdir" && \
    export EWMS_ADDRESS="https://ewms-dev.icecube.aq" && \
    export EWMS_CLIENT_SECRET=XXX && \
    export EWMS_TOKEN_URL="https://keycloak.
    icecube.wisc.edu/auth/realms/IceCube" && \
    export EWMS_CLIENT_ID="ewms-tms-dev" && \
    export TMS_ENV_VARS_AND_VALS_ADD_TO_PILOT="_EWMS_PILOT_APPTAINER_BUILD_WORKDIR=/srv/var_tmp/" && \
    apptainer run \
        --mount type=bind,source=$PWD,dst=$PWD \
        --mount type=bind,source=/etc/condor/,dst=/etc/condor/,ro \
        --mount type=bind,source=/usr/local/libexec/condor,dst=/usr/local/libexec/condor,ro \
        /cvmfs/icecube.opensciencegrid.org/containers/ewms/observation-management-service/ewms-task-management-service\:A.B.C
```
