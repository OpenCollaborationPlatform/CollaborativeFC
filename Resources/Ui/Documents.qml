
import QtQuick 2.0
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Rectangle {
    id: rectangle
    height: 70
    radius: 3
    Button {
        id: button
        x: 548
        y: 18
        text: qsTr("Edit")
        anchors.right: parent.right
        anchors.rightMargin: 8
    }

    Text {
        id: text1
        y: 12
        text: qsTr("MyDocument")
        anchors.left: parent.left
        font.pixelSize: 20
        anchors.leftMargin: 47
    }

    Button {
        id: button1
        x: 453
        y: 18
        width: 89
        height: 34
        text: qsTr("Open")
    }

    Button {
        id: button2
        x: 378
        y: 18
        width: 77
        height: 34
        text: qsTr("Join")
    }

    BorderImage {
        id: borderImage
        x: 8
        y: 16
        width: 24
        height: 20
        source: "../Icons/icon.svg"
    }

    Text {
        id: text2
        x: 47
        y: 42
        text: qsTr("Local")
        font.pixelSize: 12
    }

    Text {
        id: text3
        x: 91
        y: 42
        text: qsTr("2 Members")
        font.pixelSize: 12
    }

    Text {
        id: text4
        x: 179
        y: 42
        text: qsTr("1 Joined")
        font.pixelSize: 12
    }

}


