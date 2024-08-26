<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/Observation-Management-Service/ewms-task-management-service?include_prereleases)](https://github.com/Observation-Management-Service/ewms-task-management-service/) [![Lines of code](https://img.shields.io/tokei/lines/github/Observation-Management-Service/ewms-task-management-service)](https://github.com/Observation-Management-Service/ewms-task-management-service/) [![GitHub issues](https://img.shields.io/github/issues/Observation-Management-Service/ewms-task-management-service)](https://github.com/Observation-Management-Service/ewms-task-management-service/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/Observation-Management-Service/ewms-task-management-service)](https://github.com/Observation-Management-Service/ewms-task-management-service/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen)
<!--- End of README Badges (automated) --->

# ewms-task-management-service

A Task Management Service for EWMS

The TMS is the central component responsible for communication between the [WMS](https://github.com/Observation-Management-Service/ewms-workflow-management-service) and an [HTCondor](https://htcondor.org/) pool. It runs on an HTCondor access point (AP). This service:

- **Starts** condor clusters for new taskforces (1:1), see [taskforce](https://github.com/Observation-Management-Service/ewms-workflow-management-service#taskforce).
- **Stops** condor clusters (`condor_rm`) when necessary.
- **Watches** condor clusters, aggregates taskforce-level stats, and relays information to the WMS.

## Overview

In short, the TMS receives its instructions from the Workflow Management Service ([WMS](https://github.com/Observation-Management-Service/ewms-workflow-management-service)).

### Starting and Stopping Taskforces/Clusters

Internally, the service makes routine calls to the WMS to determine whether to start or stop clusters for specific taskforces.

### Watching the Job Event Logs

Concurrently, the service sends updates to the WMS for each taskforce in a job event log. Taskforces share a job event log if they start on the same day. A new file is created as needed, and files are deleted after a period of inactivity.

For statelessness, when the TMS restarts, aggregated taskforce updates will be re-sent to the WMS, which handles these appropriately.

## How to Build

The `image-publish.yml` GitHub Actions workflow publishes this package as an Apptainer image in CVMFS when a new release is made.

## How to Run

Replace the placeholder values, then run this as a one-liner _on sub-2_:

```bash
cd /scratch/$USER && \
    export TMS_WATCHER_INTERVAL=15 && \
    export JOB_EVENT_LOG_DIR="$PWD/tms_scratchdir" && \
    export EWMS_ADDRESS="https://ewms-dev.icecube.aq" && \
    export EWMS_CLIENT_SECRET=XXX && \
    export EWMS_TOKEN_URL="https://keycloak.icecube.wisc.edu/auth/realms/IceCube" && \
    export EWMS_CLIENT_ID="ewms-tms-dev" && \
    export TMS_ENV_VARS_AND_VALS_ADD_TO_PILOT="_EWMS_PILOT_APPTAINER_BUILD_WORKDIR=/srv/var_tmp/" && \
    apptainer run \
        --mount type=bind,source=$PWD,dst=$PWD \
        --mount type=bind,source=/etc/condor/,dst=/etc/condor/,ro \
        --mount type=bind,source=/usr/local/libexec/condor,dst=/usr/local/libexec/condor,ro \
        /cvmfs/icecube.opensciencegrid.org/containers/ewms/observation-management-service/ewms-task-management-service:A.B.C
```

## EWMS Glossary Applied to the TMS

### Workflow

_Does not exist within the TMS._ ([Compare to WMS](https://github.com/Observation-Management-Service/ewms-workflow-management-service#workflow))

### Task

A **task** is not a first-order object in the TMS. However, each taskforce holds a reference to a container, arguments, environment variables, etc. Collectively, these comprise a task. ([Compare to WMS](https://github.com/Observation-Management-Service/ewms-workflow-management-service#task))

### Task Directive

_Does not exist within the TMS._ ([Compare to WMS](https://github.com/Observation-Management-Service/ewms-workflow-management-service#task-directive))

### Taskforce

The **taskforce** is the primary object within the TMS. It is associated with one condor cluster. See Taskforce's [`cluster_id`](https://github.com/Observation-Management-Service/ewms-workflow-management-service/blob/main/Docs/Models/TaskforceObject.md).  
([Compare to WMS](https://github.com/Observation-Management-Service/ewms-workflow-management-service#taskforce))

#### Cluster

The HTCondor **cluster** maps 1:1 with a taskforce and is used only within the context of an HTCondor pool, event log, and debugging. Unlike the [Taskforce](#taskforce), this object is not relevant in the wider EWMS context.
