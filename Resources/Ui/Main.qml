import QtQuick 2.0
import QtQuick.Layouts 1.11
import QtQuick.Controls 2.15

Pane {
    id: background
    width: 550
    height: 700
    leftPadding: 0
    rightPadding: 0
    bottomPadding: 0
    topPadding: 0

    ColumnLayout {
        id: columnLayout
        anchors.fill: parent
        spacing: 0

        Header {
            id: header
            Layout.fillWidth: true
        }

        TabBar {
            id:tabBar
            position: TabBar.Footer
            contentHeight: 25
            Layout.fillWidth: false
            Layout.alignment: Qt.AlignRight | Qt.AlignTop
            TabButton {
                id: nodeButton
                height: tabBar.contentHeight
                width: implicitWidth
                text: qsTr("Node")
            }

            TabButton {
                id: docButton
                height: tabBar.contentHeight
                width: implicitWidth
                text: qsTr("Documents")
            }
        }

        SwipeView {
            id: stackLayout
            width: 100
            height: 100
            Layout.leftMargin: 5
            Layout.rightMargin: 5
            Layout.bottomMargin: 5
            Layout.topMargin: 10
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            Layout.fillWidth: true

            currentIndex: tabBar.currentIndex


            Node {
                id: node
                Layout.fillHeight: true
                Layout.fillWidth: true
            }

            Documents {
                id: documents
                Layout.fillHeight: true
                Layout.fillWidth: true
            }
        }


    }

}
