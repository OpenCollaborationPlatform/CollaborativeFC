
import QtQuick 2
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Pane {
    id: peerView

    property int peerCount: connection.network.peerCount
    onPeerCountChanged: peerLabel.text = qsTr("Connected to %1 nodes.").arg(peerCount)

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

        RowLayout {
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            Layout.fillWidth: true
            Switch {
                id: opener
                width: 10
                text: qsTr("Show Peers.")
                rightPadding: 10
                checked: false
                Layout.fillWidth: false
            }
            Label {
                id: peerLabel
                text: qsTr("Connected to 0 nodes.")
                Layout.fillWidth: true
            }
        }

        ListView {
            id: listView
            width: 10
            height: 160
            Layout.fillHeight: true
            Layout.fillWidth: true
            model: connection.network.peers
            visible: opener.checked
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop

            delegate: Row {
                Label {
                    text: display
                }
            }
        }
    }
}
