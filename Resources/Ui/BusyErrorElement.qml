import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.11

/* Panel with busy functionality
 *
 * Purpose of this element is to become busy when a AsyncSlot is called, and to go back to
 * normal when the slot is done. It displays an error if it was raised from the slot. To
 * work correctly it must be used together with AsyncSlotObject python class. A object of
 * this class is set via "setAsyncSlotObject", and afterwards all slots called on this object
 * will trigger the component to get busy.
 */

Pane {
    id: root

    default property alias contents: placeholder.children //to place the child objects correctly
    signal asyncSlotFinished(int id) //emited when slot with given id is finished

    QtObject {
        id: internal
        property QtObject asyncSlotObject: null
        property var running: []

        function onAsyncSlotFinished(id, err, msg) {


            //check if we wait for that id, and remove it if so
            const index = internal.running.indexOf(id);
            if (index > -1) {
              internal.running.splice(index, 1);
            }

            //are all id's done?
            if (internal.running.length === 0) {
                if (err !== "") {
                    errorDialog.error = err
                }
                if (msg !== "") {
                    errorDialog.message = msg
                }
                if (err !== "" || msg !== "") {
                    errorDialog.open()
                }

                stopBusy()
            }

            root.asyncSlotFinished(id)
        }

        function onAsyncSlotStarted(id) {
            startBusy()
            internal.running.push(id)
        }

        function startBusy() {
            root.enabled = false
            busy.running = true
        }

        function stopBusy() {
            root.enabled = true
            busy.running = false
        }
    }

    function setAsyncSlotObject(obj) {
        //set the object which controls the state. Important to use the function to allow
        //disconnect on change

        //in case we are still busy, we need to end it now!
        internal.running = []
        internal.stopBusy()

        if (internal.asyncSlotObject !== null) {
            internal.asyncSlotObject.onAsyncSlotFinished.disconnect(internal.onAsyncSlotFinished)
            internal.asyncSlotObject.onAsyncSlotStartet.disconnect(internal.onAsyncSlotStarted)
        }

        internal.asyncSlotObject = obj
        internal.asyncSlotObject.onAsyncSlotFinished.connect(internal.onAsyncSlotFinished)
        internal.asyncSlotObject.onAsyncSlotStarted.connect(internal.onAsyncSlotStarted)
    }

    Item {
        //item to hold the content children
        id: placeholder
        anchors.fill: parent
    }

    BusyIndicator {
        id: busy
        running: false
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
    }

    Dialog {
        id: errorDialog

        property alias error: errLabel.text
        property alias message: msgLabel.text

        modal: true
        standardButtons: Dialog.Ok
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)

        title: qsTr("Error during operation")

        ColumnLayout {
            id: columnLayout
            anchors.fill: parent

            Label {
                id: errLabel
            }
            Label {
                id: msgLabel
            }
        }


        onAccepted: close()
    }

}


