
import QtQuick 2.0
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Pane {

    width: 300
    height: 400
    padding: 5

    StackLayout {
        id: stack
        anchors.fill: parent
        currentIndex: 0

        BusyErrorElement {
            id: docList
            Component.onCompleted: setAsyncSlotObject(ocpDocuments)

            ListView {
                id: listView
                anchors.fill: parent
                model: ocpDocuments //exposed from python (name, status, members, joined)
                delegate: Document {
                    width: listView.width

                    onEdit: {
                        docEdit.document = documentObject
                        stack.currentIndex = 1
                    }
                }
            }
        }

        BusyErrorElement {
            id: docEdit

            property var document  //the document to edit

            onDocumentChanged: {

                nameEdit.text = document.name
                docPeerList.model = document.peers

                //the documents async slots call slotFinished when done
                docEdit.setAsyncSlotObject(document)
            }

            anchors.fill: parent
            padding: 0

            ColumnLayout {
                id: columnLayout
                anchors.fill: parent


                RowLayout {
                    id: rowLayout
                    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                    Layout.fillWidth: true


                    Label {
                        id: label
                        text: qsTr("Edit Document")
                        font.pointSize: 15
                        Layout.fillWidth: true
                    }
                    ToolButton {
                        id: toolButton
                        text: qsTr("Close")
                        font.bold: true
                        Layout.alignment: Qt.AlignRight | Qt.AlignVCenter

                        onClicked: stack.currentIndex = 0
                    }
                }

                TextField {
                    id: nameEdit
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                    placeholderText: qsTr("Document Name")

                    onEditingFinished: docEdit.document.setName(text)
                }

                ListView {
                    id: docPeerList
                    Layout.bottomMargin: 10
                    Layout.topMargin: 10
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    delegate: DocumentPeer {
                        documentObject: docEdit.document
                    }
                }

                RowLayout {
                    id: rowLayout1
                    width: 100
                    height: 100
                    Layout.fillWidth: true

                    TextField {
                        id: addNodeId
                        Layout.fillWidth: true
                        placeholderText: qsTr("Node ID")
                    }

                    CheckBox {
                        id: editCheckBox
                        text: qsTr("Edit rigths")
                    }

                    ToolButton {
                        id: toolButton1
                        text: qsTr("Add")

                        onClicked: {
                            docEdit.document.addPeer(addNodeId.text, editCheckBox.checked)
                            editCheckBox.checked = false
                        }
                    }

                }
            }
        }
    }
}
