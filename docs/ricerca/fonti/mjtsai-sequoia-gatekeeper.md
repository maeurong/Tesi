## Sequoia Removes Gatekeeper Contextual Menu Override

[Jason Snell](https://zeppelin.flights/@jsnell/112719231341410760):

> Here’s a thing I noticed today. macOS Sequoia changes how non-notarized apps are handled on first launch. I couldn’t override by doing the control-click > Open > yes really Open dance. Instead, I had to go to the Settings app, to the Security screen, and click there to allow it to open. At which point it asked me AGAIN if I wanted to open it, and then had to put in my password!
> 
> I get the impulse about making it harder to socially engineer bad apps from opening, but… this is ridiculous.

Apparently, after the first time of going through System Settings, you can just use the contextual menu like before. But who’s going to figure this out on their own? It’s another take on security through obscurity.

With Mac notarization increasingly difficult to bypass, it becomes even more important that Apple not add a [human](https://mjtsai.com/blog/2024/03/17/ios-notarizations-human-review/) element to it, like with iOS, where it could be weaponized to “review” apps that aren’t in the Mac App Store.

Meanwhile, the more pressing concern for me is that a significant number of my customers continue to encounter the [Gatekeeper](https://mjtsai.com/blog/2020/12/14/damaged-apps-that-cant-be-opened/) [bug](https://mjtsai.com/blog/2024/01/16/resolving-trusted-execution-problems/) where it refuses to launch (notarized!) apps because it incorrectly reports them as damaged. The Control-click bypass never worked in this case. I don’t know how to reproduce the bug except that it seems to be related to downloading a new version of an app that had previously been installed.

[Jeff Johnson](https://mastodon.social/@lapcatsoftware/112719286724628849):

> Apple keeps twisting the screw to lock down the Mac.

Previously:

- [Apple Removes VPN Apps From Russian App Store](https://mjtsai.com/blog/2024/07/05/apple-removes-vpn-apps-from-russian-app-store/)
- [UTM Blocked Outside App Store via Notarization](https://mjtsai.com/blog/2024/06/14/utm-blocked-outside-app-store-via-notarization/)
- [AltStore PAL](https://mjtsai.com/blog/2024/05/02/altstore-pal/)
- [iOS Notarization’s Human Review](https://mjtsai.com/blog/2024/03/17/ios-notarizations-human-review/)
- [Resolving Trusted Execution Problems](https://mjtsai.com/blog/2024/01/16/resolving-trusted-execution-problems/)
- [How Ventura Checks the Security of Apps and Tools](https://mjtsai.com/blog/2023/07/06/how-ventura-checks-the-security-of-apps-and-tools/)
- [“Damaged” Apps That Can’t Be Opened](https://mjtsai.com/blog/2020/12/14/damaged-apps-that-cant-be-opened/)
- [Catalina Removes Malware Assurance](https://mjtsai.com/blog/2019/12/16/catalina-removes-malware-assurance/)
- [Gatekeeper Override for Indirect Launching](https://mjtsai.com/blog/2019/11/26/gatekeeper-override-for-indirect-launching/)
- [Catalina Notarization](https://mjtsai.com/blog/2019/10/17/catalina-notarization/)
- [The True and False Security Benefits of Mac App Notarization](https://mjtsai.com/blog/2019/04/22/the-true-and-false-security-benefits-of-mac-app-notarization/)
- [macOS 10.14.5 Requires New Developers to Notarize](https://mjtsai.com/blog/2019/04/08/macos-10-14-5-requires-new-developers-to-notarize/)

> In macOS Sequoia, users will no longer be able to Control-click to override [Gatekeeper](https://developer.apple.com/developer-id/) when opening software that isn’t signed correctly or notarized. They’ll need to visit System Settings > Privacy & Security to review security information for software before allowing it to run.

[Jeff Johnson](https://mastodon.social/@lapcatsoftware/112916473677170532):

> It’s gotten worse since the first macOS 15 beta:
> 
> In the first beta, once you allowed the first app to open in System Settings, subsequent apps could be allowed to open via the contextual menu.
> 
> In the latest beta, the rules don’t change, and you can never allow apps to open via the contextual menu, only in System Settings.

[Nick Heer](https://pxlnv.com/linklog/macos-sequoia-gatekeeper/):

> This is one of those little things which will go unnoticed by most users, but will become a thorn in the side of anyone who relies on it. These are likely developers and other people who are more technologically literate placed in the position of increasingly fighting with the tools they use to get things done. It may be a small thing, but small things add up.

[Dominik Wagner](https://mastodon.social/@monkeydom/112916402060897273):

> The end of non-notarized software for regular users seems nigh.

[John Gruber](https://daringfireball.net/linked/2024/08/07/mac-os-15-sequoia-gatekeeper) ([Mastodon](https://mastodon.social/@daringfireball/112924109179096545)):

> I mean, if there are exploits running wild because unsophisticated Mac users are Control-clicking malware apps they’ve somehow downloaded, where are they? I can only see two possible explanations for these changes: (a) these decisions that are making MacOS increasingly annoying for expert and power users are being made by cover-your-ass bureaucrats for no good reason, and no one who knows better is shooting them down within Apple; or (b) there’s a serious rash of unreported abuse of these features and Apple is too timid to publicize them to justify the increased frequency and arduousness of these permission nags, lest they admit the Mac has any problems at all.

See also: [MacRumors](https://www.macrumors.com/2024/08/06/macos-sequoia-gatekeeper-security-change/), [AppleInsider](https://appleinsider.com/articles/24/08/06/apple-removes-control-click-option-for-skipping-gatekeeper-in-macos-sequoia), and [Hacker](https://news.ycombinator.com/item?id=41184553) [News](https://news.ycombinator.com/item?id=41185052).

Previously:

- [Sequoia Screen Recording Prompts and the Persistent Content Capture Entitlement](https://mjtsai.com/blog/2024/08/08/sequoia-screen-recording-prompts-and-the-persistent-content-capture-entitlement/)

> As there’s some confusion as to exactly what’s going on, this article explains how this should work, and what benefits notarization brings in return for this added inconvenience.

Previously:

- [The Mac Is a Power Tool](https://mjtsai.com/blog/2024/08/12/the-mac-is-a-power-tool/)

> Malware authors are more clever than ever. One of the latest trends is cloning real applications, often productivity apps like Notion or Slack, and injecting malware somewhere in the code. Authors then create install screens like the one below, instructing the user to right-click and open the malware to get around Gatekeeper. The crazy part is that sometimes users will go on to use these applications for quite some time and never know their system has been infected. Persistence is key for cybercriminals.

I don’t understand how making the override more difficult solves the problem of the user being tricked by a fake app.

> Once again, I don’t doubt that unsigned apps are a vector for malware and scamware and that Apple has the best intentions in trying to prevent people from launching them unawares. But this new approach, which involves nearly a half-dozen steps, goes *way* too far. It crosses a line, I think, between Apple trying to protect the user and Apple aggressively trying to poison any app that would defy its notarization scheme.
> 
> Apple has promised to let you run any software you want on your Mac, but it never promised it wouldn’t make the process painful, I guess. I don’t like it. This is just too much.

> When an app is being launched for the first time on that Mac, if it has been put into quarantine with a quarantine extended attribute, Gatekeeper will check whether it has been notarized. If it has, then its launch will progress to further checks such as those of XProtect. If it hasn’t been notarized, then macOS will warn you of that, and halt its launch.
> 
> \[…\]
> 
> If you want to launch the app despite that warning, open Privacy & Security settings, where you can click the button to **Open Anyway**.

> The `spctl` command line utility used to allow full manual control of Gatekeeper. In macOS Sequoia, it has lost most of its power, but you can still use it to re-enable the **Anywhere** option in **System Settings -> Privacy & Security -> Allow applications from** using this command:
> 
> ```
> spctl --global-disable
> ```
> 
> \[…\]
> 
> As a developer, I realize that it is now virtually impossible to release any Mac apps without having a developer account.

Previously:

- [Sequoia’s spctl and csrutil](https://mjtsai.com/blog/2024/09/23/sequoias-spctl-and-csrutil/)

> Cato Security researcher Tara Gould [reports](https://www.cadosecurity.com/blog/from-the-depths-analyzing-the-cthulhu-stealer-malware-for-macos) that Cthulhu Stealer disguises itself as popular software to trick users into installing it. It might appear as CleanMyMac, *Grand Theft Auto IV*, or even Adobe GenP (a tool some users employ to bypass Adobe’s subscription model). The malware comes packaged as a disk image (DMG) file.
> 
> If a user tries to open the fake app, macOS’s built-in security feature, Gatekeeper, warns that the software is unsigned. But if a user chooses to bypass this warning, the malware immediately asks for the user’s system password, mimicking a legitimate system prompt. This technique isn’t new – other Mac malware like [Atomic Stealer](https://www.macrumors.com/2023/04/28/atomic-macos-stealer-malware/) and MacStealer use similar tricks.

> Training users to expect seemingly random permission dialogs and requests to enter their system password is one of the worst security UX things Apple has done to macOS.
> 
> It trains you to stop caring or paying attention to the permission requests, because there are just so many of them.

Previously:

- [Notarized Atomic Stealer (AMOS)](https://mjtsai.com/blog/2025/07/17/notarized-atomic-stealer-amos/)

## 18 Comments RSS · Twitter · Mastodon

---

If they move that app that they might be updating to the Desktop first and then Command+Drag it to the Application Folder would it make any difference?

---

We need to reject this. Apple has very clearly worked to lock down the Mac slow enough that people will get acclimated to it before they move onto the next increase in lockdown

It's pretty obvious their next step is making it impossible to run unsigned apps from the GUI at all, with the end goal of requiring the App Store to install apps at all

I'm sure some people will say I'm jumping to conclusions. I can't tell the future, but I can see patterns. Apple has been ratcheting up the locked down control of Mac OS

It's not going to stop until we speak up and say this is the line they can't keep crossing and they have to walk it back

---

Manx

That won't go over very well in the EU.

---

I'm too cynical and jaded to think there's anything we can do to convince Apple to change course. They haven't been listening to devs, much less users, for over a decade. They're not addressing bugs. All of their security theater has been disastrous and pointless. They seem to be full of institutional dysfunction.

Basically I expect that every release of macOS will continue to be worse than the last, as has generally been the pattern since at the very least macOS 10.14, until it finally becomes an unusable locked down mess like iOS.

---

and yet you/we keep buying Apple devices…

---

Gatekeeper has been lying about downloads being damaged since before Notarization, I think, and I never figured out a pattern to it. Security updates be damned: Apple's security theater (and breaking 32 bit applications) is the reason I'm happy on Mojave at home. As a last resort, I've been toying with Linux on my 2008 MBP (El Capitan), just to get an up-to-date web browser. Not sure the hell of Linux graphics drivers for that ancient system is better or worse than a bunch of broken websites, but I expect it to be more solvable than Apple's decline.

---

I knew \*instinctively\* what was going on and just how to solve it.

The ratchet won't stop turning. The beatings will continue. Too many devs are apologists for Apple and can't turn back now. This was evident since the introduction of Gatekeeper. Sorry.

Apple's supported hardware path is great. A Mac is also the only way to run macOS and in particular the nice software for it. Til there's general-purpose ARM hw that you can run Linux and/or Doze on, with full out-of-box driver support, I think Macs are the least worst option. But by God, as soon as my options widen, I'll jump. The other guys need to understand that Apple's strength really is "the whole widget"; once they break that spell, techies will all swarm off a cliff, just like the lemmings in that commercial.

---

Any idea if manually removing the quarantine flag also works? Are we still allowed to turn off Gatekeeper?

---

@Bri Yes and yes, AFAICS. The CLI trick of "sudo spctl --master-disable" still works, but it re-arms after a time (I think 30 days), because reasons.

---

Apple will always do whys best for its customers.

---

A long time developer made a YT video highlighting the degradation, not specifically this issue, but the macOS in general:

[https://www.youtube.com/watch?v=3uGeHdNMgL8](https://www.youtube.com/watch?v=3uGeHdNMgL8)

---

@CowMonkey: very interesting video. Thanks!

---

@CowMonkey I wasn't expecting to watch the whole thing, but I did! I largely agree with him. He definitely gets what made classic macs so great.

---

@old coot, is macOS an EU gatekeeper platform? If not, EU can pound sand.

Also, the golden age of desktop Linux is still a couple decades away. And frankly, we should be aiming for proper sandboxing, privacy dialogs, etc.

That it doesn’t work perfectly now doesn’t mean Apple should give it up… if anything, shows why we need to do it… malware is very lucrative.

---

@Someone else  
Golden age of Desktop Linux has been, checks calendar, the last 9 years for me. It's so much easier than supporting an aging fleet of Macs that Apple had abandoned. Now I grab pretty much any computing device with an open boot loader and just run Linux. It's not perfect, but since I have to also maintain Windows systems too, let me tell you, it's not so bad sometimes either. MacOS and Windows have their own super annoying "quirks". To be clear, I've been using desktop Linux since 2004, first as a companion to my Mac use, this 11 years later, as a full replacement.

---

@CowMonkey  
While I don't dislike Bryan Lunduke per se, he has some outlandish takes on many things tech adjacent. Also, to give you a deeper cut from the wayback, I have a personal distaste for how he and his buddy destroyed the Resexcellence.com website back in the day. Lot of cool Mac history was lost for good bit as they were busy running the site into the ground. The Linux Action Show wasn't too bad though. So there's that.

---

What about removing the Gatekeeper flag from the file system? Can the app then run?

Does Gatekeeper only block downloads through a browser or is curl also part of it now?