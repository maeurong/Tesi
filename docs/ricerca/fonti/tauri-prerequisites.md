In order to get started building your project with Tauri you’ll first need to install a few dependencies:

## System Dependencies

Follow the link to get started for your respective operating system:

- [Linux](#linux) (see below for specific distributions)
- [macOS Catalina (10.15) and later](#macos)
- [Windows 7 and later](#windows)

### Linux

Tauri requires various system dependencies for development on Linux. These may be different depending on your distribution but we’ve included some popular distributions below to help you get setup.

- [Debian](#tab-panel-6917)
- [Arch](#tab-panel-6918)
- [Fedora](#tab-panel-6919)
- [Gentoo](#tab-panel-6920)
- [OSTree](#tab-panel-6921)
- [openSUSE](#tab-panel-6922)
- [Alpine](#tab-panel-6923)
- [NixOS](#tab-panel-6924)

```sh
sudo apt update
sudo apt install libwebkit2gtk-4.1-dev \
  build-essential \
  curl \
  wget \
  file \
  libxdo-dev \
  libssl-dev \
  libayatana-appindicator3-dev \
  librsvg2-dev
```

If your distribution isn’t included above then you may want to check [Awesome Tauri on GitHub](https://github.com/tauri-apps/awesome-tauri#guides) to see if a guide has been created.

Next: [Install Rust](#rust)

### macOS

Tauri uses [Xcode](https://developer.apple.com/xcode/resources/) and various macOS and iOS development dependencies.

Download and install Xcode from one of the following places:

- [Mac App Store](https://apps.apple.com/gb/app/xcode/id497799835?mt=12)
- [Apple Developer website](https://developer.apple.com/xcode/resources/).

Be sure to launch Xcode after installing so that it can finish setting up.

Only developing for desktop targets? If you’re only planning to develop desktop apps and not targeting iOS then you can install Xcode Command Line Tools instead:

```sh
xcode-select --install
```

Next: [Install Rust](#rust)

### Windows

Tauri uses the Microsoft C++ Build Tools for development as well as Microsoft Edge WebView2. These are both required for development on Windows.

Follow the steps below to install the required dependencies.

#### Microsoft C++ Build Tools

1. Download the [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) installer and open it to begin installation.
2. During installation check the “Desktop development with C++” option.

![Visual Studio C++ Build Tools installer screenshot](https://v2.tauri.app/_astro/visual-studio-build-tools-installer.BWhlyd8N_J78Jx.webp)

Next: [Install WebView2](#webview2).

#### WebView2

Tauri uses Microsoft Edge WebView2 to render content on Windows.

Install WebView2 by visiting the [WebView2 Runtime download section](https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section). Download the “Evergreen Bootstrapper” and install it.

Next: [Check VBSCRIPT](#vbscript-for-msi-installers)

#### VBSCRIPT (for MSI installers)

Building MSI packages on Windows requires the VBSCRIPT optional feature to be enabled. This feature is enabled by default on most Windows installations, but may have been disabled on some systems.

If you encounter errors like `failed to run light.exe` when building MSI packages, you may need to enable the VBSCRIPT feature:

1. Open **Settings** → **Apps** → **Optional features** → **More Windows features**
2. Locate **VBSCRIPT** in the list and ensure it’s checked
3. Click **Next** and restart your computer if prompted

**Note:** VBSCRIPT is currently enabled by default on most Windows installations, but is [being deprecated](https://techcommunity.microsoft.com/blog/windows-itpro-blog/vbscript-deprecation-timelines-and-next-steps/4148301) and may be disabled in future Windows versions.

Next: [Install Rust](#rust)

## Rust

Tauri is built with [Rust](https://www.rust-lang.org/) and requires it for development. Install Rust using one of following methods. You can view more installation methods at [https://www.rust-lang.org/tools/install](https://www.rust-lang.org/tools/install).

- [Linux and macOS](#tab-panel-6925)
- [Windows](#tab-panel-6926)

Install via [`rustup`](https://github.com/rust-lang/rustup) using the following command:

```sh
curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh
```

**Be sure to restart your Terminal (and in some cases your system) for the changes to take effect.**

Next: [Configure for Mobile Targets](#configure-for-mobile-targets) if you’d like to build for Android and iOS, or, if you’d like to use a JavaScript framework, [install Node](#nodejs). Otherwise [Create a Project](https://v2.tauri.app/start/create-project/).

## Node.js

1. Go to the [Node.js website](https://nodejs.org/), download the Long Term Support (LTS) version and install it.
2. Check if Node was successfully installed by running:

```sh
node -v
# v20.10.0
npm -v
# 10.2.3
```

It’s important to restart your Terminal to ensure it recognizes the new installation. In some cases, you might need to restart your computer.

While npm is the default package manager for Node.js, you can also use others like pnpm or yarn. To enable these, run `corepack enable` in your Terminal. This step is optional and only needed if you prefer using a package manager other than npm.

Next: [Configure for Mobile Targets](#configure-for-mobile-targets) or [Create a project](https://v2.tauri.app/start/create-project/).

## Configure for Mobile Targets

If you’d like to target your app for Android or iOS then there are a few additional dependencies that you need to install:

- [Android](#android)
- [iOS](#ios)

### Android

1. Download and install [Android Studio from the Android Developers website](https://developer.android.com/studio)
2. Set the `JAVA_HOME` environment variable:

- [Linux](#tab-panel-6914)
- [macOS](#tab-panel-6915)
- [Windows](#tab-panel-6916)

```sh
export JAVA_HOME=/opt/android-studio/jbr
```

3. Use the SDK Manager in Android Studio to install the following:
- Android SDK Platform
- Android SDK Platform-Tools
- NDK (Side by side)
- Android SDK Build-Tools
- Android SDK Command-line Tools

Selecting “Show Package Details” in the SDK Manager enables the installation of older package versions. Only install older versions if necessary, as they may introduce compatibility issues or security risks.

4. Set `ANDROID_HOME` and `NDK_HOME` environment variables.

- [Linux](#tab-panel-6927)
- [macOS](#tab-panel-6928)
- [Windows](#tab-panel-6929)

```sh
export ANDROID_HOME="$HOME/Android/Sdk"
export NDK_HOME="$ANDROID_HOME/ndk/$(ls -1 $ANDROID_HOME/ndk)"
```

5. Add the Android targets with `rustup`:

```sh
rustup target add aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android
```

Next: [Setup for iOS](#ios) or [Create a project](https://v2.tauri.app/start/create-project/).

### iOS

1. Add the iOS targets with `rustup` in Terminal:

```sh
rustup target add aarch64-apple-ios x86_64-apple-ios aarch64-apple-ios-sim
```

2. Install [Homebrew](https://brew.sh/):

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

3. Install [Cocoapods](https://cocoapods.org/) using Homebrew:

```sh
brew install cocoapods
```

Next: [Create a project](https://v2.tauri.app/start/create-project/).

## Troubleshooting

If you run into any issues during installation be sure to check the [Troubleshooting Guide](https://v2.tauri.app/develop/debug/) or reach out on the [Tauri Discord](https://discord.com/invite/tauri).

Next Steps

Now that you’ve installed all of the prerequisites you’re ready to [create your first Tauri project](https://v2.tauri.app/start/create-project/)!