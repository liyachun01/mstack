// One-time fallback for an authorized NEW key dialog when Electron omits AX text.
// Never prints OCR text, a key, or an image. Existing keys are not opened.
import Cocoa
import Vision
import Foundation
import Darwin

var privateCapture: URL?
func fail(_ message: String) -> Never {
    if let path = privateCapture { try? FileManager.default.removeItem(at: path) }
    print(message); exit(1)
}
let args = Array(CommandLine.arguments.dropFirst())
guard args.count == 2 else { fail("Expected private target file and exact new channel name") }
let target = URL(fileURLWithPath: args[0])
guard !FileManager.default.fileExists(atPath: target.path), target.path.contains("/.secrets/") else { fail("Private new credential target required") }
guard let app = NSRunningApplication.runningApplications(withBundleIdentifier: "com.anytype.anytype").first else { fail("Anytype not running") }
let windows = (CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]]) ?? []
let owned = windows.filter { ($0[kCGWindowOwnerPID as String] as? Int32) == app.processIdentifier && ($0[kCGWindowLayer as String] as? Int) == 0 }
guard owned.count == 1, let number = owned[0][kCGWindowNumber as String] as? Int else { fail("Ambiguous Anytype window") }
umask(0o077)
let capture = target.deletingLastPathComponent().appendingPathComponent("new-key-" + UUID().uuidString + ".png")
privateCapture = capture
defer { try? FileManager.default.removeItem(at: capture) }
let process = Process()
process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
process.arguments = ["-x", "-l", String(number), capture.path]
try process.run(); process.waitUntilExit()
guard process.terminationStatus == 0 else { fail("Private capture failed") }
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
try VNImageRequestHandler(url: capture).perform([request])
let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
let heading = lines.joined(separator: " ").lowercased()
guard heading.contains("api"), heading.contains("creada correctamente") || heading.contains("successfully created") || heading.contains("se ha creado la clave de api") else { fail("Not a newly created API key dialog") }
// Vision can recognize the key's lowercase x as a multiplication glyph.
// The candidate is still authenticated and scope-checked before it is saved.
let compact = lines.map { $0.replacingOccurrences(of: " ", with: "").replacingOccurrences(of: "×", with: "x") }
let pattern = try NSRegularExpression(pattern: "any[A-Za-z0-9_-]{20,}")
var candidates = Set<String>()
for (index, line) in compact.enumerated() {
    for match in pattern.matches(in: line, range: NSRange(line.startIndex..., in: line)) {
        if let range = Range(match.range, in: line) {
            var candidate = String(line[range])
            for next in compact.dropFirst(index + 1).prefix(1) {
                guard next.range(of: "^[a-z0-9_-]{8,}$", options: .regularExpression) != nil else { break }
                candidate += next
            }
            candidates.insert(candidate)
        }
    }
}
guard candidates.count == 1, let key = candidates.first else { fail("New key could not be read unambiguously; no value emitted") }
print("Recognized credential length:", key.count)
func get(_ path: String) -> [String: Any]? {
    var req = URLRequest(url: URL(string: "http://127.0.0.1:31009" + path)!)
    req.setValue("Bearer " + key, forHTTPHeaderField: "Authorization")
    let done = DispatchSemaphore(value: 0)
    var result: [String: Any]?
    URLSession.shared.dataTask(with: req) { data, response, _ in
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        print("Credential validation HTTP status:", status)
        if status == 200, let data = data { result = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] }
        done.signal()
    }.resume()
    guard done.wait(timeout: .now() + 15) == .success else { return nil }
    return result
}
guard let who = get("/v2/auth/whoami"), let grant = who["grant"] as? [String: Any],
      grant["all_spaces"] as? Bool == false, grant["permission"] as? String == "readwrite",
      let granted = grant["spaces"] as? [[String: Any]], granted.count == 1,
      let spaces = get("/v2/spaces?ids=full"), let rows = spaces["data"] as? [[String: Any]],
      rows.count == 1, rows[0]["name"] as? String == args[1] else { fail("New credential or exact channel grant did not validate; nothing saved") }
try Data(key.utf8).write(to: target, options: [.withoutOverwriting])
try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: target.path)
print("New credential saved privately; single-channel read/write grant verified; value omitted")
