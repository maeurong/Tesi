Hello,

I have a python script for Mac which I "compiled" to create a standalone terminal application that runs in any Mac.

The exe file created by pyinstaller runs with no error when using their own (default) signature. The command used was:  
pyinstaller --onefile pyPythonScript.py As expected, it recreate an exe file using the same name.

Now, when try to re-sign the script following the Apple notarization procedure (an have the app not blocked by Gatekeeper), the resulting signed file fails. (ONLY the sign is modified, using the following command)

codesign -s "$DevID" -o runtime -f --timestamp $compFile

where $DevID is of the form: "Developer ID Application: ENTITY NAME (TEAM ID)"  
TEAM ID would be 10 char code

Once signed as indicated above, the very same exe that was running with no issues, halted throwing the following error message:

\[698\] Error loading Python lib '/var/folders/wb/x9vsmbzd5yv2djkl8s5\_kmdw0000gn/T/\_MEIEQQltp/Python': dlopen: dlopen(/var/folders/wb/x9vsmbzd5yv2djkl8s5\_kmdw0000gn/T/\_MEIEQQltp/Python, 0x000A): tried: '/var/folders/wb/x9vsmbzd5yv2djkl8s5\_kmdw0000gn/T/\_MEIEQQltp/Python' (code signature in <80977C84-A9E5-30EF-B62C-DE085145A242> '/private/var/folders/wb/x9vsmbzd5yv2djkl8s5\_kmdw0000gn/T/\_MEIEQQltp/Python' not valid for use in process: mapped file has no Team ID and is not a platform binary (signed with custom identity or adhoc?)), '/usr/lib/Python' (no such file), '/private/var/folders/wb/x9vsmbzd5yv2djkl8s5\_kmdw0000gn/T/\_MEIEQQltp/Python' (code signature in <80977C84-A9E5-30EF-B62C-DE085145A242> '/private/var/folders/wb/x9vsmbzd5yv2djkl8s5\_kmdw0000gn/T/\_MEIEQQltp/Python' not valid for use in process: mapped file has no Team ID and is not a platform binary (signed with custom identity or adhoc?)), '/usr/lib/Python' (no such file)

No other change whatsoever was done (intentionally at least) other than replace the pyinstaller original signature for one that complies with Apple notarization procedure.

Thus, here is the dilemma: it is either you deal directly with the Mac reply when trying to access an exe file NOT being notarized (it becomes blocked by Gatekeeper) by disabling the later or you have an authorized file that does not run properly.

To make things even more complicated, the signed exe (following Apple Notarization procedures) run in certain Macs and not in others. I meant, the error described below is not consistent for all models and OS. For example, using a T2 Intel powered mac and OS 12 (Monterrey) the error did not occur. Like wise, in an older NON T2 intel running Ventura (OS 13). However, in a very similar hardware (2 years older) running Catalina (OS10.15) the error was thrown and also in a couple of M1 or M2 new Macs.

Obviously, the error are related to this file: T/\_MEIEQQltp

Any help on what is happening here? How can a access the internals of the EXE to review was going on?

Thanks!