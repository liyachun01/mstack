// Use the existing macOS Swift runtime and Accessibility permission. No install.
import Cocoa
import ApplicationServices
import Darwin

let args = Array(CommandLine.arguments.dropFirst())
guard let action = args.first, let running = NSRunningApplication.runningApplications(withBundleIdentifier: "com.anytype.anytype").first else { fatalError("Anytype is not running") }
guard AXIsProcessTrusted() else { fatalError("Existing Accessibility access is unavailable") }
_ = running.activate(options: [.activateAllWindows])
Thread.sleep(forTimeInterval: 0.4)
let app = AXUIElementCreateApplication(running.processIdentifier)
func attr(_ node: AXUIElement, _ key: String) -> CFTypeRef? {
    var v: CFTypeRef?
    guard AXUIElementCopyAttributeValue(node, key as CFString, &v) == .success else { return nil }
    return v
}
let previousManual = attr(app, "AXManualAccessibility")
let previousEnhanced = attr(app, "AXEnhancedUserInterface")
_ = AXUIElementSetAttributeValue(app, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
_ = AXUIElementSetAttributeValue(app, "AXManualAccessibility" as CFString, kCFBooleanTrue)
func restoreAccessibility() {
    if let v = previousManual { _ = AXUIElementSetAttributeValue(app, "AXManualAccessibility" as CFString, v) }
    if let v = previousEnhanced { _ = AXUIElementSetAttributeValue(app, "AXEnhancedUserInterface" as CFString, v) }
}
defer { restoreAccessibility() }
Thread.sleep(forTimeInterval: 1.0)
func collect(_ node: AXUIElement, _ depth: Int = 0) -> [AXUIElement] {
    guard depth < 30 else { return [] }
    return [node] + ((attr(node, kAXChildrenAttribute) as? [AXUIElement]) ?? []).flatMap { collect($0, depth + 1) }
}
func nodes() -> [AXUIElement] {
    for _ in 0..<10 {
        let windows = (attr(app, kAXWindowsAttribute) as? [AXUIElement]) ?? []
        let children = (attr(app, kAXChildrenAttribute) as? [AXUIElement]) ?? []
        let roots = windows.isEmpty ? children.filter { (attr($0, kAXRoleAttribute) as? String) == "AXWindow" } : windows
        if !roots.isEmpty { return roots.flatMap { collect($0) } }
        Thread.sleep(forTimeInterval: 0.2)
    }
    return []
}
func key(_ code: CGKeyCode, _ flags: CGEventFlags = []) {
    for down in [true, false] {
        let event = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: down)!
        event.flags = flags
        event.post(tap: .cghidEventTap)
    }
}
switch action {
case "snapshot":
    let windows = (CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]]) ?? []
    let owned = windows.filter { ($0[kCGWindowOwnerPID as String] as? Int32) == running.processIdentifier && ($0[kCGWindowLayer as String] as? Int) == 0 }
    for window in owned {
        print("window", window[kCGWindowNumber as String] ?? "", window[kCGWindowName as String] ?? "", window[kCGWindowBounds as String] ?? "")
    }
    fflush(stdout)
    guard let chosen = owned.max(by: { a, b in
        let x = a[kCGWindowBounds as String] as? [String: Double] ?? [:]
        let y = b[kCGWindowBounds as String] as? [String: Double] ?? [:]
        return (x["Width"] ?? 0) * (x["Height"] ?? 0) < (y["Width"] ?? 0) * (y["Height"] ?? 0)
    }), let number = chosen[kCGWindowNumber as String] as? Int else {
        restoreAccessibility()
        print("No visible Anytype window")
        exit(1)
    }
    let capture = Process()
    capture.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
    capture.arguments = ["-x", "-l", String(number), args[1]]
    try capture.run()
    capture.waitUntilExit()
    guard capture.terminationStatus == 0 else {
        restoreAccessibility()
        print("Window capture failed")
        exit(1)
    }
case "click", "click-window":
    var p = CGPoint(x: Double(args[1])!, y: Double(args[2])!)
    if action == "click-window" {
        let windows = (CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]]) ?? []
        let owned = windows.filter { ($0[kCGWindowOwnerPID as String] as? Int32) == running.processIdentifier && ($0[kCGWindowLayer as String] as? Int) == 0 }
        guard owned.count == 1, let bounds = owned[0][kCGWindowBounds as String] as? [String: Double],
              let x = bounds["X"], let y = bounds["Y"] else { fatalError("Ambiguous window; inspect before clicking") }
        p.x += x
        p.y += y
    }
    let down = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: p, mouseButton: .left)!
    down.flags = []
    down.post(tap: .cghidEventTap)
    Thread.sleep(forTimeInterval: 0.1)
    let up = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: p, mouseButton: .left)!
    up.flags = []
    up.post(tap: .cghidEventTap)
case "key":
    key(CGKeyCode(args[1])!, args.count > 2 && args[2] == "command" ? .maskCommand : [])
case "type":
    let units = Array(args[1].utf16)
    for down in [true, false] {
        let event = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: down)!
        event.flags = []
        event.keyboardSetUnicodeString(stringLength: units.count, unicodeString: units)
        event.post(tap: .cghidEventTap)
    }
case "inspect", "headings":
    for n in nodes() {
        let role = attr(n, kAXRoleAttribute) as? String ?? ""
        if action == "headings" && role != "AXHeading" { continue }
        var label = attr(n, kAXTitleAttribute) as? String ?? ""
        if label.count > 100 { label = "[long label omitted]" }
        if !label.isEmpty || ["AXTextField", "AXTextArea", "AXCheckBox", "AXPopUpButton"].contains(role) { print(role, "|", label) }
    }
case "diagnostics":
    let all = nodes()
    print("active", running.isActive, "nodes", all.count)
    print(Dictionary(grouping: all, by: { attr($0, kAXRoleAttribute) as? String ?? "" }).mapValues { $0.count })
    for n in all where (attr(n, kAXRoleAttribute) as? String) == "AXHeading" {
        for attribute in [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute] {
            if let s = attr(n, attribute) as? String, s.count < 120 { print(attribute, s) }
        }
    }
case "save-new-key":
    let all = nodes()
    let created = all.contains { n in
        let role = attr(n, kAXRoleAttribute) as? String ?? ""
        let label = (attr(n, kAXTitleAttribute) as? String ?? "").lowercased()
        return ["AXHeading", "AXStaticText"].contains(role) && label.contains("api") && (label.contains("created") || label.contains("cread"))
    }
    guard created else { fatalError("Not the newly created API key dialog") }
    let fields = all.filter { (attr($0, kAXRoleAttribute) as? String) == "AXTextArea" }
    let values = fields.compactMap { attr($0, kAXValueAttribute) as? String }.filter { $0.count >= 20 }
    guard values.count == 1 else { fatalError("New key field is ambiguous") }
    let target = URL(fileURLWithPath: args[1])
    guard !FileManager.default.fileExists(atPath: target.path) else { fatalError("Refusing to replace existing credential") }
    umask(0o077)
    try Data(values[0].utf8).write(to: target, options: [.withoutOverwriting])
    try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: target.path)
    print("New channel credential saved; value omitted")
default: fatalError("Unsupported action")
}
