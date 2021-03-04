import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Pane {
    width: 800
    height: 800
    //property alias node: node

    ColumnLayout {
        id: mainLayout
        anchors.fill: parent
        spacing: 10

        RowLayout {
            id: nodeMainLayout
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            spacing: 10
            Layout.fillWidth: true

            Rectangle {
                id: nodeIndicator
                width: 20
                height: 20
                color: connection.node.running ? "green" : "grey"
                radius: 10
                Layout.topMargin: 5
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            }

            BusyErrorElement {
                id: nodeBusy
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                Layout.fillWidth: true
                padding: 0

                Component.onCompleted: setAsyncSlotObject(connection.node)

                //required as BusyErrorElement cannot calculate its size with layouts as parent and children
                contentHeight: nodeLayout.implicitHeight

                ColumnLayout {
                    id: nodeLayout
                    width: parent.width

                    RowLayout {
                        id: nodeControlLayout
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        Layout.fillWidth: true

                        ColumnLayout {
                            id: nodeDataLayout
                            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                            Layout.fillHeight: false
                            Layout.fillWidth: true

                            Label {
                                id: nodeMessage
                                text: connection.node.running ? qsTr("OCP Node running") : qsTr("No OCP Node running")
                                font.pointSize: 15
                                Layout.fillWidth: true
                                font.bold: true
                                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                            }

                            Grid {

                                id: nodeSettingsGrid
                                Layout.fillWidth: false
                                spacing: 3
                                rows: 2
                                columns: 3
                                enabled: !connection.node.running

                                verticalItemAlignment: Grid.AlignVCenter
                                Layout.alignment: Qt.AlignLeft | Qt.AlignTop

                                Label {
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
                            id: nodeButton
                            height: 25
                            enabled: !connection.api.connected
                            text: connection.node.running ? qsTr("Shutdown") : qsTr("Startup")
                            Layout.alignment: Qt.AlignRight | Qt.AlignTop

                            onClicked: connection.node.running ? connection.node.shutdownSlot() : connection.node.runSlot()
                        }
                    }

                    LogView {
                        id: nodeLog
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                    }
                }
            }
        }

        RowLayout {
            id: apiMainLayout
            width: 100
            height: 100
            Layout.fillHeight: false
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            Layout.fillWidth: true
            spacing: 10

            Rectangle {
                id: apiIndicator
                width: 20
                height: 20
                color: connection.api.connected ? "green" : "grey"
                radius: 10
                Layout.topMargin: 5
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            }

            BusyErrorElement {
                id: apiBusy
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                Layout.fillWidth: true
                padding: 0

                Component.onCompleted: setAsyncSlotObject(connection.api)

                //required as BusyErrorElement cannot calculate its size with layouts as parent and children
                contentHeight: apiLayout.implicitHeight

              ColumnLayout {
                id: apiLayout
                width: parent.width
                spacing: 1
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop

                RowLayout {
                    id: apiControlLayout
                    width: 100
                    height: 100
                    Layout.fillHeight: false
                    Layout.fillWidth: true

                    Label {
                        id: apiMessage
                        text: connection.api.connected ? qsTr("API connection established") : qsTr("Not connected to OCP Node API")
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        Layout.fillWidth: true
                        font.bold: true
                        font.pointSize: 15
                    }

                    Button {
                        id: apiButton
                        enabled: connection.node.running
                        text: connection.api.connected ? qsTr("Disconnect") : qsTr("Connect")
                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter

                        onClicked: connection.api.connected ? connection.api.disconnectSlot() : connection.api.connectSlot()
                    }

                }

                CheckBox {
                    id: reconnectCheckbox
                    text: qsTr("Autoconnect when node is running")
                    Component.onCompleted: checked = connection.api.reconnect
                    onClicked: connection.api.reconnect = checked
                }
            }

            }
        }

        RowLayout {
            id: network
            width: 100
            height: 100
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            spacing: 10
            Layout.fillWidth: true
            enabled: connection.api.connected

            property bool connected: connection.network.peerCount > 0

            Rectangle {
                id: rectangle4
                width: 20
                height: 20
                color: network.connected ? "green" : "grey"
                radius: 10
                Layout.topMargin: 5
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            }

            ColumnLayout {
                id: columnLayout3
                width: 100
                height: 100

                Label {
                    id: label3
                    text: network.connected ? qsTr("Node connected to P2P network") : qsTr("Node cannot reach P2P network")
                    Layout.fillWidth: true
                    font.bold: true
                    font.pointSize: 15
                }

                PeerView {
                    id: peerView
                }
            }
        }

        RowLayout {
            id: rechability
            width: 100
            height: 100
            Layout.fillHeight: false
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            spacing: 10
            Layout.fillWidth: true
            enabled: connection.api.connected

            Rectangle {
                id: rectangle5
                width: 20
                height: 20
                color: connection.network.reachability === "Public" ? "green" : "grey"
                radius: 10
                Layout.topMargin: 5
                Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            }

            Label {
                id: label4
                text: qsTr("Network reachability:")
                font.bold: true
                font.pointSize: 15
            }

            Label {
                id: label5
                text: connection.network.reachability
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


