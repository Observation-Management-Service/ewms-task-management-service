<!--- Top of README Badges (automated) --->
[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/Observation-Management-Service/ewms-task-management-service?include_prereleases)](https://github.com/Observation-Management-Service/ewms-task-management-service/) [![Lines of code](https://img.shields.io/tokei/lines/github/Observation-Management-Service/ewms-task-management-service)](https://github.com/Observation-Management-Service/ewms-task-management-service/) [![GitHub issues](https://img.shields.io/github/issues/Observation-Management-Service/ewms-task-management-service)](https://github.com/Observation-Management-Service/ewms-task-management-service/issues?q=is%3Aissue+sort%3Aupdated-desc+is%3Aopen) [![GitHub pull requests](https://img.shields.io/github/issues-pr/Observation-Management-Service/ewms-task-management-service)](https://github.com/Observation-Management-Service/ewms-task-management-service/pulls?q=is%3Apr+sort%3Aupdated-desc+is%3Aopen) 
<!--- End of README Badges (automated) --->

# ewms-task-management-service v1

A Task Management Service for EWMS

The TMS is the central component responsible for communication between the [WMS](https://github.com/Observation-Management-Service/ewms-workflow-management-service) and an [HTCondor](https://htcondor.org/) pool. It runs on an HTCondor Access Point (AP). This service:

- **Starts** condor clusters for new taskforces (1:1), see [taskforce](#taskforce).
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

In production, the TMS runs on an HTCondor Access Point (AP) using systemd. Files for this are in [tms-prod/](./resources/systemd/tms-prod) and [tms-dev/](./resources/systemd/tms-dev), as well as additional helper scripts in [resources/systemd/](./resources/systemd/).

Whichever systemd variant you choose, a `envfile` is required. The file for `tms-prod` looks something like (minus the redactions):

```bash
EWMS_ADDRESS="https://ewms-prod.icecube.aq"
EWMS_CLIENT_ID="ewms-tms-prod"
EWMS_CLIENT_SECRET="XXXX"
EWMS_TOKEN_URL="https://keycloak.icecube.wisc.edu/auth/realms/IceCube"

JOB_EVENT_LOG_DIR="/.../tms-prod/jobs"

TMS_ENV_VARS_AND_VALS_ADD_TO_PILOT="_EWMS_PILOT_APPTAINER_BUILD_WORKDIR=/srv/var_tmp/"
TMS_WATCHER_INTERVAL="15"
```

## How to Update in Production

Use the helper script, [update_tms_image_symlink.sh](resources/systemd/update_tms_image_symlink.sh), to roll out a new TMS version on an HTCondor Access Point (AP) using systemd:

```bash
ewms@sub-2 ~/resources/systemd/tms-dev $ ../update_tms_image_symlink.sh v1.2.3
```

## EWMS Glossary Applied to the TMS

### Workflow

_Does not exist within the TMS._ _[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#workflow)_

### Task

A **task** is not a first-order object in the TMS. However, each taskforce holds a reference to a container, arguments, environment variables, etc. Collectively, these comprise a task. _[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#task)_

### Task Directive

_Does not exist within the TMS._ _[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#task-directive)_

### Taskforce

The **taskforce** is the primary object within the TMS. It is associated with one condor cluster. See Taskforce's [`cluster_id`](https://github.com/Observation-Management-Service/ewms-workflow-management-service/blob/main/Docs/Models/TaskforceObject.md).  
_[Compare to WMS.](https://github.com/Observation-Management-Service/ewms-workflow-management-service#taskforce)_

#### Cluster

The **cluster** is the realization of a **taskforce** within an HTCondor pool. The two are mapped 1:1 and are nearly synonymous at a high level.

However, the term "cluster" is used exclusively within the context of an HTCondor pool, the job event log, and debugging. Unlike the taskforce, the cluster is not relevant in the broader EWMS context.

Bump semver release test 1
