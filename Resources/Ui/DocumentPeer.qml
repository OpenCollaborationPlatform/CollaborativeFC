
import QtQuick 2.0
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Pane {
    id: root

    width: 500
    height: 50
    padding: 5

    property var documentObject

    RowLayout {
        id: rowLayout
        anchors.fill: parent

        ColumnLayout {
            id: columnLayout
            width: 100
            height: 100
            spacing: 3
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            Layout.fillWidth: true

            Label {
                id: label
                text: qsTr("Qm9463hd8hz57d3z4f")
                Layout.fillWidth: true
                font.bold: true
            }

            RowLayout {
                id: rowLayout1
                width: 100
                height: 100
                Layout.fillWidth: true

                Label {
                    id: label1
                    text: qsTr("Rights:")
                }

                Label {
                    id: authLabel
                    text: authorisation
                }

                Label {
                    id: label3
                    text: qsTr("Joined:")
                    Layout.leftMargin: 20
                }

                Label {
                    id: joinedLabel
                    text: joined
                }
            }
        }

        Button {
            id: rigthButton
            width: 70
            text: qsTr("Read Only")
            flat: true
            Layout.alignment: Qt.AlignRight | Qt.AlignTop

            onClicked: documentObject.togglePeerRigths(index)
        }

        Button {
            id: removeButton
            width: 70
            text: qsTr("Remove")
            flat: true
            Layout.alignment: Qt.AlignRight | Qt.AlignTop

            onClicked: documentObject.removePeer(index)
        }

    }
}
