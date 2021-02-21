
import QtQuick 2.0
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

Pane {
    id: rectangle
    width: 200
    height: 400
    padding: 5

    ListView {
        id: listView
        anchors.fill: parent
        model: ocpDocuments //exposed from python (name, status, members, joined)
        delegate: Document {
            width: listView.width
        }
    }
}


