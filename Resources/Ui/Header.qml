
import QtQuick 2.0
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Rectangle {
    id: header
    width: 400
    height: 60
    color: "#222222"
    
    RowLayout {
        id: rowLayout
        anchors.fill: parent
        anchors.rightMargin: 5
        anchors.leftMargin: 5
        anchors.bottomMargin: 10
        anchors.topMargin: 5
        spacing: 10

        Image {
            id: image
            width: 40
            height: 40
            horizontalAlignment: Image.AlignLeft
            verticalAlignment: Image.AlignBottom
            source: "../Icons/icon_white.svg"
            antialiasing: true
            smooth: true
            Layout.fillHeight: true
            sourceSize.height: heigth
            sourceSize.width: width
            Layout.maximumWidth: 50
            Layout.maximumHeight: 50
            Layout.alignment: Qt.AlignLeft | Qt.AlignBottom
            fillMode: Image.PreserveAspectFit
        }

        ColumnLayout {
            id: columnLayout
            spacing: 0
            Layout.fillHeight: false
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignLeft | Qt.AlignBottom

            Text {
                id: text1
                color: "#ffffff"
                text: qsTr("FreeCAD Collaboration")
                font.pixelSize: 20
                font.bold: true
                Layout.fillWidth: true
            }

            RowLayout {
                id: idRow
                spacing: 10
                layoutDirection: Qt.LeftToRight

                Text {
                    id: text2
                    color: "#ffffff"
                    text: qsTr("Node ID:")
                    font.pixelSize: 12
                }

                TextEdit {
                    id: nodeIdText
                    width: 80
                    height: 20
                    color: "#ffffff"
                    font.pixelSize: 12
                    selectByMouse: true
                    readOnly: true
                    text: connection.network.nodeId
                    mouseSelectionMode: TextInput.SelectCharacters
                }
            }
        }

    }


}



/*##^##
Designer {
    D{i:0;formeditorZoom:1.1}
}
##^##*/
