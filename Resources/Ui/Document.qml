import QtQuick 2.0
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Pane {
    id: root
    width: 500
    height: 60
    padding: 0
    leftPadding: 0
    rightPadding: 0
    bottomPadding: 0
    topPadding: 0

    property string docStatus: status

    onDocStatusChanged: {
        if (docStatus == "shared"  || docStatus == "node" ) {
            shareButton.shared = true
            openButton.enabled = true
            editButton.enabled = true
        } else {
            shareButton.text = qsTr("Share")
            shareButton.shared = false
            openButton.enabled = false
            editButton.enabled = false
        }
    }

    RowLayout {
        id: rowLayout
        anchors.fill: parent
        spacing: 10

        ColumnLayout {
            id: columnLayout
            width: 100
            height: 100
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            spacing: 2
            Layout.fillWidth: true

            Label {
                id: docNameLabel
                Layout.preferredWidth: root.width - buttons.width - 10
                text: name
                elide: Text.ElideRight
                font.pointSize: 15
            }

            Row {
                id: row
                width: 200
                height: 400
                spacing: 20

                Label {
                    id: docStatusLabel
                    text: status
                }

                Label {
                    id: docMembersLabel
                    property int count: members
                    text: qsTr("0 Members")
                    onCountChanged: text = qsTr("%1 Members").arg(count)
                }

                Label {
                    id: docActiveLabel
                    property int count: joined
                    text: qsTr("0 Joined")
                    onCountChanged: text = qsTr("%1 Joined").arg(count)
                }
            }
        }

        RowLayout {
            id: rowLayout1
            spacing: 1
            Layout.alignment: Qt.AlignRight | Qt.AlignTop
        }

        Row {
            id: buttons
            width: 200
            height: 400
            spacing: 1
            Layout.alignment: Qt.AlignRight | Qt.AlignTop

            Button {
                id: shareButton
                width: implicitWidth*0.6
                flat: true
                property bool shared: false

                text: shared ? qsTr("Stop") : qsTr("Start")
                onClicked: shared ? ocpDocuments.stopCollaborateSlot(index) : ocpDocuments.collaborateSlot(index)
            }

            Button {
                id: openButton
                width: implicitWidth*0.6

                display: AbstractButton.TextOnly
                flat: true

                text: isOpen ? qsTr("Close") : qsTr("Open")
                onClicked: isOpen ? ocpDocuments.closeSlot(index) : ocpDocuments.openSlot(index)
            }

            Button {
                id: editButton
                width: implicitWidth*0.6
                text: qsTr("Edit")
                display: AbstractButton.TextOnly
                flat: true
                //onClicked: root.edit()
            }

        }

    }
    
}


