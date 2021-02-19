
import QtQuick 2
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Pane {
    width: 200
    height: 300
    clip: true
    rightPadding: 0
    leftPadding: 0
    bottomPadding: 0
    topPadding: 0

    ColumnLayout {
        id: columnLayout1
        anchors.fill: parent
        anchors.rightMargin: 0

        Switch {
            id: opener
            width: 10
            text: qsTr("Show Logs")
            checked: false
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
        }

        ListView {
            id: listView
            width: 10
            height: 160
            Layout.fillHeight: true
            Layout.fillWidth: true
            model: connection.node.logModel
            visible: opener.checked

            delegate: Row {
                Label {
                    width: 170
                    text: time
                }
                Label {
                    width: 50
                    text: level
                }
                Label {
                    text: message
                }
            }
        }
    }
}
