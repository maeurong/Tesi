![](https://peter.sh/images/grass.jpg)

These are the 1,093 command line switches and 3,152 feature flags defined in [Chromium](https://source.chromium.org/chromium/chromium/src) as of September 11, 2026.

To apply feature flags to Chrome, append them to the end of the executable path when launching the browser from a command prompt. For example, running chrome --enable-features=Feature1,Feature2 launches a session with those capabilities enabled, and chrome --disable-features=Feature3 can be used to disable them. Command line switches can be appended to the executable path directly.

| Type | Name | Description | Source |

_Estratto: solo le righe pertinenti alla ricerca (--app, --app-id, --user-data-dir, --window-size, --no-first-run) dalla tabella completa di 1.093 switch; pagina intera 1,2 MB non conservata._

| Type | Name | Description | Source |
| --- | --- | --- | --- |
| Switch | \--app | Specifies that the associated value should be launched in "application" mode. | [source](https://source.chromium.org/chromium/chromium/src/+/main:chrome/common/chrome_switches.h;l=89?q=kApp) |
| Switch | \--app-id | Sorted in the lexicographical order. | [source](https://source.chromium.org/chromium/chromium/src/+/main:ash/constants/chrome_switches.h;l=16?q=kAppId) |
| Switch | \--app-id | Specifies that the extension-app with the specified id should be launched according to its configuration. | [source](https://source.chromium.org/chromium/chromium/src/+/main:chrome/common/chrome_switches.h;l=93?q=kAppId) |
| Switch | \--no-first-run | Skip First Run tasks as well as not showing additional dialogs, prompts or bubbles. Suppressing dialogs, prompts, and bubbles is important as this switch is used by automation (including performance benchmarks) where it's important only a browser window is shown. This may not actually be the first run or the What's New page. Its effect can be partially ignored by adding kForceFirstRun (for FRE), kForceWhatsNew (for What's New) and/or kIgnoreNoFirstRunForSearchEngineChoiceScreen (for the DSE choice screen). This does not drop the First Run sentinel and thus doesn't prevent first run from occurring the next time chrome is launched without this flag. It also does not update the last What's New milestone, so does not prevent What's New from occurring the next time chrome is launched without this flag. | [source](https://source.chromium.org/chromium/chromium/src/+/main:chrome/common/chrome_switches.h;l=526?q=kNoFirstRun) |
| Switch | \--user-data-dir | Makes Content Shell use the given path for its data directory. NOTE: "user-data-dir" is used to align with Chromedriver's behavior. Please do NOT change this to another value. NOTE: The same value is also used at Java-side in ContentShellBrowserTestActivity.java#getUserDataDirectoryCommandLineSwitch(). | [source](https://source.chromium.org/chromium/chromium/src/+/main:content/shell/common/shell_switches.h;l=21?q=kContentShellUserDataDir) |
| Switch | \--user-data-dir | Specifies the user data directory, which is where the browser will look for all of its state. | [source](https://source.chromium.org/chromium/chromium/src/+/main:chrome/common/chrome_switches.h;l=764?q=kUserDataDir) |
| Switch | \--window-size | Specify the initial window size: --window-size=w,h | [source](https://source.chromium.org/chromium/chromium/src/+/main:chrome/common/chrome_switches.h;l=815?q=kWindowSize) |
