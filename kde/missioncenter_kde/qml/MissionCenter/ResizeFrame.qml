import QtQuick
import QtQuick.Window

// Invisible grips along the window edges that hand resizing to the
// compositor (works on Wayland, where clients can't move their own edges).
Item {
    id: frame

    required property Window window
    property real grip: 6
    property real corner: 16

    component Grip: Item {
        id: g
        property int edges: 0
        property int cursor: Qt.ArrowCursor
        visible: frame.enabled
        HoverHandler { cursorShape: g.cursor }
        DragHandler {
            target: null
            onActiveChanged: if (active) frame.window.startSystemResize(g.edges)
        }
    }

    // edges
    Grip { x: frame.corner; width: parent.width - 2 * frame.corner; height: frame.grip; edges: Qt.TopEdge; cursor: Qt.SizeVerCursor }
    Grip { x: frame.corner; y: parent.height - frame.grip; width: parent.width - 2 * frame.corner; height: frame.grip; edges: Qt.BottomEdge; cursor: Qt.SizeVerCursor }
    Grip { y: frame.corner; width: frame.grip; height: parent.height - 2 * frame.corner; edges: Qt.LeftEdge; cursor: Qt.SizeHorCursor }
    Grip { x: parent.width - frame.grip; y: frame.corner; width: frame.grip; height: parent.height - 2 * frame.corner; edges: Qt.RightEdge; cursor: Qt.SizeHorCursor }
    // corners
    Grip { width: frame.corner; height: frame.corner; edges: Qt.TopEdge | Qt.LeftEdge; cursor: Qt.SizeFDiagCursor }
    Grip { x: parent.width - frame.corner; width: frame.corner; height: frame.corner; edges: Qt.TopEdge | Qt.RightEdge; cursor: Qt.SizeBDiagCursor }
    Grip { y: parent.height - frame.corner; width: frame.corner; height: frame.corner; edges: Qt.BottomEdge | Qt.LeftEdge; cursor: Qt.SizeBDiagCursor }
    Grip { x: parent.width - frame.corner; y: parent.height - frame.corner; width: frame.corner; height: frame.corner; edges: Qt.BottomEdge | Qt.RightEdge; cursor: Qt.SizeFDiagCursor }
}
