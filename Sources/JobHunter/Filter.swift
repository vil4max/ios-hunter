import Foundation

func isIOSJob(title: String) -> Bool {
    let pattern =
        #"(?i)(?<![A-Za-z0-9])(ios|swift|swiftui|uikit|objective[\s\-]?c|objc|obj[\s\-]?c|xcode|iphone|ipad|tvos|watchos|visionos|cocoa(?:pods|touch)?)(?![A-Za-z0-9])"#
    return title.range(of: pattern, options: .regularExpression) != nil
}
