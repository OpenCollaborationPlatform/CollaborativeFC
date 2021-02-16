import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Pane {
    width: 800
    height: 800

    ColumnLayout {
        id: columnLayout1
        anchors.fill: parent

        RowLayout {
            id: rowLayout
            width: 100
            height: 100
            spacing: 10
            Layout.fillWidth: true

            Rectangle {
                id: rectangle
                width: 20
                height: 20
                color: connection.node.running ? "green" : "grey"
                radius: 10
                Layout.topMargin: 5
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            }

            ColumnLayout {
                id: columnLayout4
                width: 100
                height: 100

                RowLayout {
                    id: rowLayout1
                    width: 100
                    height: 100

                    ColumnLayout {
                        id: columnLayout
                        width: 100
                        height: 100
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        Layout.fillHeight: false
                        Layout.fillWidth: true

                        Label {
                            id: text3
                            text: connection.node.running ? qsTr("OCP Node running") : qsTr("No OCP Node available")
                            font.pixelSize: 20
                            Layout.fillWidth: true
                            font.bold: true
                            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        }

                        Grid {

                            id: grid
                            spacing: 3
                            rows: 2
                            columns: 3

                            verticalItemAlignment: Grid.AlignVCenter
                            Layout.alignment: Qt.AlignLeft | Qt.AlignTop

                            Label {
                                id: label
                                text: qsTr("P2P listens on")
                                rightPadding: 10
                            }

                            TextField {
                                id: p2pUri
                                width: 130
                                text: connection.node.p2pUri
                                placeholderText: qsTr("IP Adress")
                            }

                            TextField {
                                id: p2pPort
                                width: 60
                                text: connection.node.p2pPort
                                placeholderText: qsTr("Port")
                            }

                            Label {
                                id: label1
                                text: qsTr("API listen on")
                                rightPadding: 10
                            }

                            TextField {
                                id: wampUri
                                width: 130
                                text: connection.node.apiUri
                                placeholderText: qsTr("IP Adress")
                            }

                            TextField {
                                id: wampPort
                                width: 60
                                text: connection.node.apiPort
                                placeholderText: qsTr("Port")
                            }


                        }


                    }

                    Button {
                        id: button
                        height: 25
                        text: connection.node.running ? qsTr("Shutdown") : qsTr("Startup")
                        Layout.alignment: Qt.AlignRight | Qt.AlignTop

                        onClicked: connection.node.running ? connection.shutdown() : connection.startup()
                    }
                }

                LogView {
                    id: logView
                }


            }



        }

        RowLayout {
            id: rowLayout4
            width: 100
            height: 100
            Layout.fillHeight: true
            Layout.fillWidth: true

            ColumnLayout {
                id: columnLayout2
                width: 100
                height: 100
                Layout.fillHeight: true
                Layout.fillWidth: true
                Layout.topMargin: 5
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop

                Rectangle {
                    id: rectangle3
                    width: 20
                    height: 20
                    color: "#288404"
                    radius: 10
                }

                Rectangle {
                    id: rectangle4
                    width: 20
                    height: 20
                    color: "#288404"
                    radius: 10
                }
            }

            Rectangle {
                id: rectangle2
                width: 390
                height: 233
                radius: 5
                border.color: "#666666"
                border.width: 1
                Layout.fillHeight: true
                Layout.fillWidth: true

                ColumnLayout {
                    id: columnLayout3
                    anchors.fill: parent
                    anchors.rightMargin: 5
                    anchors.leftMargin: 5
                    anchors.bottomMargin: 5
                    anchors.topMargin: 5

                    Text {
                        id: text6
                        text: qsTr("OCP Node can reach the network")
                        font.pixelSize: 12
                        font.bold: true
                    }

                    Text {
                        id: text1
                        text: qsTr("Node cannot be reached from other peers")
                        font.pixelSize: 12
                        font.bold: true
                        Layout.topMargin: 5
                    }

                    ListView {
                        id: listView
                        width: 374
                        height: 129
                        Layout.topMargin: 20
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        delegate: Item {
                            x: 5
                            id: row1
                            implicitHeight: text20.height
                            Text {
                                id: text20
                                text: name
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                        model: ListModel {
                            ListElement {
                                name: "Grey"
                                colorCode: "grey"
                            }

                            ListElement {
                                name: "Red"
                                colorCode: "red"
                            }

                            ListElement {
                                name: "Blue"
                                colorCode: "blue"
                            }

                            ListElement {
                                name: "Green"
                                colorCode: "green"
                            }
                        }
                    }
                }
            }
        }

    }


}


