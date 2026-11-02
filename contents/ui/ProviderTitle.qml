pragma ComponentBehavior: Bound
import QtQuick

QtObject {
    property string provider: "antigravity"
    property bool rounded: false
    property string mode: "legacy"
    property string customText: ""
    readonly property bool automatic: mode === "auto" || (mode !== "custom" &&
        (!customText || ["antigravity.sh", "antigravity.exe", "codex.sh"].indexOf(customText) !== -1))
    readonly property string automaticText: rounded ? (provider === "codex" ? "Codex" : "Antigravity") :
                                                     (provider === "codex" ? "codex.sh" : "antigravity.sh")
    readonly property string text: automatic ? automaticText : customText
}
