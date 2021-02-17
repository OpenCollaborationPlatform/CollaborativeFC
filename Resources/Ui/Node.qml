import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Pane {
    width: 800
    height: 800
    property alias rowLayout: rowLayout

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
                Layout.fillWidth: true

                RowLayout {
                    id: rowLayout1
                    width: 100
                    height: 100
                    Layout.fillWidth: true

                    ColumnLayout {
                        id: columnLayout
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        Layout.fillHeight: false
                        Layout.fillWidth: true

                        Label {
                            id: text3
                            text: connection.node.running ? qsTr("OCP Node running") : qsTr("No OCP Node running")
                            font.pointSize: 15
                            Layout.fillWidth: true
                            font.bold: true
                            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        }

                        Grid {

                            id: grid
                            Layout.fillWidth: false
                            spacing: 3
                            rows: 2
                            columns: 3
                            enabled: !connection.node.running

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

                                onEditingFinished: connection.node.setP2PDetails(p2pUri.text,  p2pPort.text)
                            }

                            TextField {
                                id: p2pPort
                                width: 60
                                text: connection.node.p2pPort
                                placeholderText: qsTr("Port")

                                onEditingFinished: connection.node.setP2PDetails(p2pUri.text,  p2pPort.text)
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

                                onEditingFinished: connection.node.setAPIDetails(apiUri.text,  apiPort.text)
                            }

                            TextField {
                                id: wampPort
                                width: 60
                                text: connection.node.apiPort
                                placeholderText: qsTr("Port")

                                onEditingFinished: connection.node.setAPIDetails(apiUri.text,  apiPort.text)
                            }
                        }
                    }

                    Button {
                        id: button
                        height: 25
                        enabled: !connection.api.connected
                        text: connection.node.running ? qsTr("Shutdown") : qsTr("Startup")
                        Layout.alignment: Qt.AlignRight | Qt.AlignTop

                        onClicked: connection.node.running ? connection.node.shutdownSlot() : connection.node.runSlot()
                    }
                }

                LogView {
                    id: logView
                    Layout.fillWidth: true
                    Layout.fillHeight: false
                }


            }



        }

        RowLayout {
            id: rowLayout5
            width: 100
            height: 100
            Layout.fillWidth: true
            spacing: 10

            Rectangle {
                id: rectangle3
                width: 20
                height: 20
                color: connection.api.connected ? "green" : "grey"
                radius: 10
                Layout.topMargin: 5
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            }

            ColumnLayout {
                id: columnLayout2
                width: 100
                height: 100
                enabled: connection.node.running
                spacing: 1
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop

                RowLayout {
                    id: rowLayout4
                    width: 100
                    height: 100
                    Layout.fillHeight: false
                    Layout.fillWidth: true

                    Label {
                        id: label2
                        text: connection.api.connected ? qsTr("API connection established") : qsTr("Not connected to OCP Node API")
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        Layout.fillWidth: true
                        font.bold: true
                        font.pointSize: 15
                    }

                    Button {
                        id: button1
                        enabled: connection.node.running
                        text: connection.api.connected ? qsTr("Disconnect") : qsTr("Connect")
                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter

                        onClicked: connection.api.connected ? connection.api.disconnectSlot() : connection.api.connectSlot()
                    }

                }

                CheckBox {
                    id: reconnectCheckbox
                    text: qsTr("Autoconnect when node is running")
                    checked: connection.api.reconnect

                    onCheckStateChanged: connection.api.reconnect = reconnectCheckbox.checked
                }
            }

        }

        RowLayout {
            id: rowLayout2
            width: 100
            height: 100
            Layout.fillWidth: true

            Rectangle {
                id: rectangle4
                width: 20
                height: 20
                color: "grey"
                radius: 10
            }

            Label {
                id: label3
                text: qsTr("Node connected to network")
                Layout.fillWidth: true
                font.bold: true
                font.pointSize: 15
            }
        }

        RowLayout {
            id: rowLayout3
            width: 100
            height: 100
            Layout.fillWidth: true
            Rectangle {
                id: rectangle5
                width: 20
                height: 20
                color: "grey"
                radius: 10
            }

            Label {
                id: label4
                text: qsTr("Reachable by other nodes")
                Layout.fillWidth: true
                font.bold: true
                font.pointSize: 15
            }
        }

        Pane {
            id: pane
            width: 200
            height: 200
            Layout.fillHeight: true
            Layout.fillWidth: true
        }



    }


}

