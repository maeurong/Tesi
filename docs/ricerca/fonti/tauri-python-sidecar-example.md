# README.md (dieharders/example-tauri-v2-python-server-sidecar)

Fonte: https://github.com/dieharders/example-tauri-v2-python-server-sidecar/blob/master/README.md

```markdown
# Example Tauri v2 app using Python sidecar

A native app built with Tauri version 2 that spawns a Python sub-process (sidecar) which starts a FastAPI server.

<div align="center">

[Download the example app and try out](https://github.com/dieharders/example-tauri-v2-python-server-sidecar/releases)

![Python](https://img.shields.io/badge/-Python-000?&logo=Python)
![TypeScript](https://img.shields.io/badge/-TypeScript-000?&logo=TypeScript)
![Rust](https://img.shields.io/badge/-Rust-000?&logo=Rust)
<br/>
![FastAPI](https://img.shields.io/badge/-FastAPI-000?&logo=fastapi)
![NextJS](https://img.shields.io/badge/-NextJS-000?&logo=nextdotjs)
![Tauri](https://img.shields.io/badge/-Tauri-000?&logo=Tauri)

</div>

![logo](extras/sidecar-logo.png "python sidecar logo")

## Table of Contents

- [Introduction](#introduction)
- [How It Works](#how-it-works)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Deploy using your machine](#deploy-using-your-machine)
- [Deploy using Github Actions](#deploy-using-github-actions)
- [Issues](#issues)
- [Todo's](#todos)
- [Learn More](#learn-more)

## Introduction

> [!NOTE]
>
> <strong>Tauri v1 example also available:
> <a href="https://github.com/dieharders/example-tauri-python-server-sidecar" style="color: #228be6">example-tauri-python-server-sidecar</a></strong>

This example app uses Next.js as the frontend and Python (FastAPI) as the backend. Tauri is a Rust framework that orchestrates the frontend and backend(s) into a native app experience.

This template project is intended to demonstrate the use of single file Python executables with Tauri v2.

![app screenshot](extras/screenshot.png "app screenshot")

Tauri "sidecars" allow developers to package dependencies to make installation easier on the user. Tauri's API allows the frontend to communicate with any runtime and give it access to the OS disk, camera, and other native hardware features. This is defined in the `tauri.conf.json` file. See [here](https://v2.tauri.app/develop/sidecar/) for more info.

## How It Works

![python sidecar architecture](extras/diagram.png "python sidecar architecture")

- Tauri takes your frontend UI written in html/javascript and displays it in a native webview. This makes the resulting file size smaller since it does not need to include a web browser (as Electron.js requires).

- [PyInstaller](https://pyinstaller.org/en/stable/) is used to compile a binary of the Python code so users don't have to worry about installing dependencies.

- In `main.rs` we spawn a python binary (sidecar) called `main.exe` which starts an api server on `localhost:8008`. The frontend tells Tauri to startup and shutdown the sidecar via stdin/stdout commands. <em>Note, we cannot use process.kill() for one-file Python executables since Tauri only knows the pid of the PyInstaller bootloader process and not its' child process (which is actually the sidecar)</em>.

- If you are not comfortable coding in Rust, do not worry, this example orchestrates things in a way so you only need concern yourself with communication between your frontend and server (sidecar) via http.

- When the GUI window is closed, the server and python processes are shutdown properly.

## Features

This should give you everything you need to build a local, native application that can use other programs to perform specialized work (like a server, llm engine or database).

- Launch and communicate with any binary or runtime written in any language. This example uses a Python executable.

- Communicate between frontend (javascript) and backend (Python) server via http.

- IPC communication between frontend (javascript) and Tauri (Rust) framework.

- Also control this app from an external UI source like another website, app or terminal. As long as it uses http(s) and you whitelist the url in the server config `main.py`.

## Project Structure

These are the important project folders to understand.

```bash
/app # (frontend code, js/html/css)
/src/backends # (backend code, the "sidecar")
/src-tauri
  |  /bin/api # (compiled sidecar is put here)
  |  /icons # (app icons go here)
  |  /src/main.rs # (Tauri main app logic)
  |  tauri.conf.json # (Tauri config file for app permissions, etc.)
package.json # (build scripts)
```

## Getting Started

### Dependencies

Install all dependencies for javascript and Python:

```bash
pnpm install-reqs
```

Or install javascript dependencies only:

```bash
pnpm install
```

Or install dependencies for Python only. Be sure to run with admin privileges. Recommend creating a virtual env:

```
pip install -r requirements.txt
```

Tauri requires icons in the appropriate folder. Run the script to automatically generate icons from a source image. I have included icons for convenience.

```bash
pnpm build:icons
```

### Run

Run the app in development mode:

```bash
pnpm tauri dev
```

## Deploy using your machine

### 1. Compile Python sidecar

Run this at least once before running `pnpm tauri dev` or `pnpm tauri build` and each time you make changes to your python code:

```bash
pnpm build:sidecar-winos
# OR
pnpm build:sidecar-macos
# OR
pnpm build:sidecar-linux
```

In case you dont have PyInstaller installed run:

```
pip install -U pyinstaller
```

A note on compiling Python exe (the -F flag bundles everything into one .exe). You won't need to run this manually each build, I have included it in the build scripts.

### 2. Build Next.js (optional)

Build the static html files that tauri will serve as your front-end.

```bash
pnpm run build
```

### 3. Build tauri (and Next.js)

Tauri will run the "build" script (which does the same as the previous step) before it builds the tauri app, see `tauri.conf.json` file. You can edit what script it runs in the `beforeBuildCommand`.
Build the production app on your machine for a specific OS:

```bash
pnpm tauri build
```

This creates an installer located here:

- `<project-dir>\src-tauri\target\release\bundle\nsis`

And the raw executable here:

- `<project-dir>\src-tauri\target\release`

## Deploy using Github Actions

Fork this repo in order to access a manual trigger to build for each platform (Windows, MacOS, Linux) and upload a release.

You can then modify the `release.yml` file to suit your specific app's build pipeline needs. Workflow permissions must be set to "Read and write". Any git tags created before a workflow existed will not be usable for that workflow. You must specify a tag to run from (not a branch name).

Initiate the Workflow Manually:

1. Navigate to the "Actions" tab in your GitHub repository.
2. Select the "Manual Tauri Release" workflow.
3. Click on "Run workflow" and provide the necessary inputs:

   - release_name: The title of the release.
   - release_notes (optional): Notes or changelog for the release.
   - release_type: ("draft", "public", "private")

## Issues?

- "Failed to fetch" error: In `src/backends/main.py` CORS expects your UI is running on localhost:3000. If not, add your url to the `origins = []` array or set:

```python
app.add_middleware(
  allow_origins="*" # whitelist everything
)
```

## Todo's

- Example api endpoint that demonstrates handling file paths for `--add-data` files and using `sys._MEIPASS` to find the path relative to the production executable.

- Pass parameters to the sidecar (like server port) via a frontend form.

- Pass argument `--dev-sidecar` to `pnpm tauri dev` script that tells Tauri to run sidecars in "dev mode". This would allow for running the python code from the python interpreter installed on your machine rather than having to manually compile with `pnpm build:sidecar-[os]` each time you make changes to the Python code.

- Develop a standalone multi-sidecar manager that can handle startup/shutdown and communication between all other sidecars spawned in the app.

## Learn More

- [Tauri Framework](https://tauri.app/) - learn about native app development in javascript and rust.
- [NextJS](https://nextjs.org/docs) - learn about the popular react framework Next.js
- [FastAPI](https://fastapi.tiangolo.com/) - learn about FastAPI server features and API.
- [PyInstaller](https://pyinstaller.org/en/stable/) - learn about packaging python code.
```
