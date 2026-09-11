## Supported runners and hardware resources

Ranges of GitHub-hosted runners are available for use in public and private repositories.

For lists of available runners, see:

- [Standard runners for **public** repositories](#standard-github-hosted-runners-for-public-repositories)
- [Standard runners for **private** repositories](#standard-github-hosted-runners-for--private-repositories)

GitHub-hosted Linux runners support hardware acceleration for Android SDK tools, which makes running Android tests much faster and consumes fewer minutes. For more information on Android hardware acceleration, see [Configure hardware acceleration for the Android Emulator](https://developer.android.com/studio/run/emulator-acceleration) in the Android Developers documentation.

### Standard GitHub-hosted runners for public repositories

For public repositories, jobs using the workflow labels shown in the table below will run with the associated specifications. With the exception of single-CPU runners, each GitHub-hosted runner is a new virtual machine (VM) hosted by GitHub. Single-CPU runners are hosted in a container on a shared VM—see [GitHub-hosted runners reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners#single-cpu-runners). Use of the standard GitHub-hosted runners is free and unlimited on public repositories.

| **Virtual machine / container** | **Processor (CPU)** | **Memory (RAM)** | **Storage (SSD)** | **Architecture** | **Workflow label** |
| --- | --- | --- | --- | --- | --- |
| Linux | 1 | 5 GB | 14 GB | x64 | `ubuntu-slim` |
| Linux | 4 | 16 GB | 14 GB | x64 | `ubuntu-latest`, `ubuntu-24.04`, `ubuntu-22.04`, `ubuntu-26.04` (Public preview) |
| Windows | 4 | 16 GB | 14 GB | x64 | `windows-latest`, `windows-2025`, `windows-2025-vs2026`, `windows-2022` |
| Linux | 4 | 16 GB | 14 GB | arm64 | `ubuntu-24.04-arm`, `ubuntu-22.04-arm`, `ubuntu-26.04-arm` (Public preview) |
| Windows | 4 | 16 GB | 14 GB | arm64 | `windows-11-arm`, `windows-11-vs2026-arm` |
| macOS | 4 | 14 GB | 14 GB | Intel | `macos-15-intel`, `macos-26-intel` |
| macOS | 3 (M1) | 7 GB | 14 GB | arm64 | `macos-latest`, `macos-14`, `macos-15`, `macos-26`, `xcode-27` (Public preview) |

### Standard GitHub-hosted runners for private repositories

For private repositories, jobs using the workflow labels shown in the table below will run on virtual machines with the associated specifications. These runners use your GitHub account's allotment of free minutes, and are then charged at the per minute rates. See [Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing).

| **Virtual Machine** | **Processor (CPU)** | **Memory (RAM)** | **Storage (SSD)** | **Architecture** | **Workflow label** |
| --- | --- | --- | --- | --- | --- |
| Linux | 1 | 5 GB | 14 GB | x64 | `ubuntu-slim` |
| Linux | 2 | 8 GB | 14 GB | x64 | `ubuntu-latest`, `ubuntu-24.04`, `ubuntu-22.04`, `ubuntu-26.04` (Public preview) |
| Windows | 2 | 8 GB | 14 GB | x64 | `windows-latest`, `windows-2025`, `windows-2022` |
| Linux | 2 | 8 GB | 14 GB | arm64 | `ubuntu-24.04-arm`, `ubuntu-22.04-arm`, `ubuntu-26.04-arm` (Public preview) |
| Windows | 2 | 8 GB | 14 GB | arm64 | `windows-11-arm`, `windows-11-vs2026-arm` |
| macOS | 4 | 14 GB | 14 GB | Intel | `macos-15-intel`, `macos-26-intel` |
| macOS | 3 (M1) | 7 GB | 14 GB | arm64 | `macos-latest`, `macos-14`, `macos-15`, `macos-26`, `xcode-27` (Public preview) |

Workflow logs list the runner used to run a job. For more information, see [Viewing workflow run history](https://docs.github.com/en/actions/how-tos/monitor-workflows/view-workflow-run-history).

### Limitations for arm64 macOS runners

- All actions provided by GitHub are compatible with arm64 GitHub-hosted runners. However, community actions may not be compatible with arm64 and need to be manually installed at runtime.
- Nested-virtualization is not supported due to the limitation of Apple's Virtualization Framework.
- Networking capabilities such as Azure private networking and assigning static IPs are not currently available for macOS larger runners.
- The arm64 macOS runners do not have a static UUID/UDID assigned to them because Apple does not support this feature. However, Intel MacOS runners are assigned a static UDID, specifically `4203018E-580F-C1B5-9525-B745CECA79EB`. If you are building and signing on the same host you plan to test the build on, you can sign with a [development provisioning profile](https://developer.apple.com/help/account/provisioning-profiles/create-a-development-provisioning-profile/). If you do require a static UDID, you can use Intel runners and add their UDID to your Apple Developer account.

### Single-CPU runners

Single-CPU GitHub-hosted runners are available in both public and private repositories. These runners—specified using the workflow label `ubuntu-slim` —offer a lower-cost option for running lightweight operations. This type of runner is optimized for automation tasks, issue operations and short-running jobs. They are not suitable for typical heavyweight CI/CD builds.

`ubuntu-slim` runners execute Actions workflows in Ubuntu Linux, inside a container rather than a full VM instance. When the job begins, GitHub automatically provisions a new container for that job. All steps in the job execute in the container, allowing the steps in that job to share information using the runner's file system. When the job has finished, the container is automatically decommissioned. Each container provides hypervisor level 2 isolation.

A minimal set of tools is installed on the `ubuntu-slim` runner image, appropriate for lightweight tasks. For details on what software is installed on the `ubuntu-slim` image, see the [README file](https://github.com/actions/runner-images/blob/main/images/ubuntu-slim/ubuntu-slim-Readme.md) in the `actions/runner-images` repository.

#### Usage limits

Single-CPU runners follow the same concurrency model as other GitHub-hosted standard runners. See [Actions limits](https://docs.github.com/en/actions/reference/limits#job-concurrency-limits-for-github-hosted-runners). The concurrency for the runners is determined by your plan.

The job timeout for single-CPU runners is 15 minutes. If a job reaches this limit, the job is terminated and fails.

### Larger runners

Larger runners are available for organizations and enterprises on GitHub Team and GitHub Enterprise Cloud plans.

Larger runners are managed virtual machines with more resources than [standard GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners#supported-runners-and-hardware-resources). They offer the following advanced features:

- More RAM, CPU, and disk space
- Static IP addresses
- Azure private networking
- The ability to group runners
- Autoscaling to support concurrent workflows
- GPU-powered runners

These larger runners are hosted by GitHub and have the runner application and other tools preinstalled.

For more information, see [Using larger runners](https://docs.github.com/en/actions/how-tos/manage-runners/larger-runners).

## Administrative privileges

The Linux and macOS virtual machines both run using passwordless `sudo`. When you need to execute commands or install tools that require more privileges than the current user, you can use `sudo` without needing to provide a password. For more information, see the [Sudo Manual](https://www.sudo.ws/man/1.8.27/sudo.man.html).

Windows virtual machines are configured to run as administrators with User Account Control (UAC) disabled. For more information, see [How User Account Control works](https://docs.microsoft.com/windows/security/identity-protection/user-account-control/how-user-account-control-works) in the Windows documentation.

## IP addresses

To get a list of IP address ranges that GitHub Actions uses for GitHub-hosted runners, you can use the GitHub REST API. For more information, see the `actions` key in the response of the `GET /meta` endpoint. For more information, see [REST API endpoints for meta data](https://docs.github.com/en/rest/meta/meta#get-github-meta-information).

Windows and Ubuntu runners are hosted in Azure and subsequently have the same IP address ranges as the Azure datacenters. macOS runners are hosted in GitHub's own macOS cloud.

Since there are so many IP address ranges for GitHub-hosted runners, we do not recommend that you use these as allowlists for your internal resources. Instead, we recommend you use larger runners with a static IP address range, or self-hosted runners. For more information, see [Using larger runners](https://docs.github.com/en/actions/how-tos/manage-runners/larger-runners) or [Self-hosted runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners).

The list of GitHub Actions IP addresses returned by the API is updated once a week.

## Communication requirements for GitHub-hosted runners

A GitHub-hosted runner must establish connections to GitHub-owned endpoints to perform essential communication operations. In addition, your runner may require access to additional networks that you specify or utilize within an action.

To ensure proper communications for GitHub-hosted runners between networks within your configuration, ensure that the following communications are allowed.

**Needed for essential operations:**

```shell
github.com
api.github.com
*.actions.githubusercontent.com
```

**Needed for downloading actions:**

```shell
codeload.github.com
```

**Needed for uploading/downloading job summaries, logs, workflow artifacts, and caches:**

```shell
results-receiver.actions.githubusercontent.com
*.blob.core.windows.net
```

**Needed for runner version updates:**

```shell
objects.githubusercontent.com
objects-origin.githubusercontent.com
github-releases.githubusercontent.com
github-registry-files.githubusercontent.com
```

**Needed for retrieving OIDC tokens:**

```shell
*.actions.githubusercontent.com
```

**Needed for downloading or publishing packages or containers to GitHub Packages:**

```shell
*.pkg.github.com
pkg-containers.githubusercontent.com
ghcr.io
```

**Needed for Git Large File Storage**

```shell
github-cloud.githubusercontent.com
github-cloud.s3.amazonaws.com
```

**Needed for jobs for Dependabot updates**

```shell
dependabot-actions.githubapp.com
```

**Needed for downloading release assets:**

```shell
release-assets.githubusercontent.com
```

**Needed for VNet:**

```shell
api.snapcraft.io
*.core.windows.net
```

## File systems

GitHub executes actions and shell commands in specific directories on the virtual machine. The file paths on virtual machines are not static. Use the environment variables GitHub provides to construct file paths for the `home`, `workspace`, and `workflow` directories.

| Directory | Environment variable | Description |
| --- | --- | --- |
| `home` | `HOME` | Contains user-related data. For example, this directory could contain credentials from a login attempt. |
| `workspace` | `GITHUB_WORKSPACE` | Actions and shell commands execute in this directory. An action can modify the contents of this directory, which subsequent actions can access. |
| `workflow/event.json` | `GITHUB_EVENT_PATH` | The `POST` payload of the webhook event that triggered the workflow. GitHub rewrites this each time an action executes to isolate file content between actions. |

For a list of the environment variables GitHub creates for each workflow, see [Store information in variables](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables).

### Docker container filesystem

Actions that run in Docker containers have static directories under the `/github` path. However, we strongly recommend using the default environment variables to construct file paths in Docker containers.

GitHub reserves the `/github` path prefix and creates three directories for actions.

- `/github/home`
- `/github/workspace` - **Note:** GitHub Actions must be run by the default Docker user (root). Ensure your Dockerfile does not set the `USER` instruction, otherwise you will not be able to access `GITHUB_WORKSPACE`.
- `/github/workflow`