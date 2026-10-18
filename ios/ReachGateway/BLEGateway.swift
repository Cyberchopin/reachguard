import CoreBluetooth
import Foundation

/// CoreBluetooth central for the Reach firmware GATT service. Foreground only:
/// no background modes are declared. All delegate callbacks run on the main
/// queue and are forwarded to the owner through closures.
final class BLEGateway: NSObject {
    enum LinkState: Equatable {
        case bluetoothUnavailable(String)
        case scanning
        case connecting
        case discovering
        case ready      // subscribed to Alert notifications
        case reconnecting
    }

    var onLinkState: ((LinkState) -> Void)?
    var onAlertData: ((Data, _ peripheralID: String) -> Void)?
    var onStatusData: ((Data) -> Void)?
    /// Called once per ACK write, in write order; nil error means the
    /// firmware's GATT server returned a write response.
    var onAckWriteResult: ((Error?) -> Void)?

    private let serviceUUID = CBUUID(string: ReachGATT.service)
    private let alertUUID = CBUUID(string: ReachGATT.alert)
    private let ackUUID = CBUUID(string: ReachGATT.ack)
    private let statusUUID = CBUUID(string: ReachGATT.status)

    private var central: CBCentralManager!
    private var peripheral: CBPeripheral?
    private var ackCharacteristic: CBCharacteristic?

    func start() {
        central = CBCentralManager(delegate: self, queue: .main)
    }

    /// Returns false if there is no connected Ack characteristic to write to.
    func writeAck(_ packet: Data) -> Bool {
        guard let peripheral, peripheral.state == .connected, let ackCharacteristic else { return false }
        peripheral.writeValue(packet, for: ackCharacteristic, type: .withResponse)
        return true
    }

    private func scan() {
        guard central.state == .poweredOn else { return }
        ackCharacteristic = nil
        central.scanForPeripherals(withServices: [serviceUUID])
        onLinkState?(.scanning)
    }
}

extension BLEGateway: CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        switch central.state {
        case .poweredOn: scan()
        case .unauthorized: onLinkState?(.bluetoothUnavailable("未授权蓝牙（设置 > 隐私 > 蓝牙）"))
        case .poweredOff: onLinkState?(.bluetoothUnavailable("蓝牙已关闭"))
        case .unsupported: onLinkState?(.bluetoothUnavailable("设备不支持 BLE"))
        default: onLinkState?(.bluetoothUnavailable("蓝牙状态未知"))
        }
    }

    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral,
                        advertisementData: [String: Any], rssi RSSI: NSNumber) {
        central.stopScan()
        self.peripheral = peripheral
        peripheral.delegate = self
        central.connect(peripheral)
        onLinkState?(.connecting)
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        onLinkState?(.discovering)
        peripheral.discoverServices([serviceUUID])
    }

    func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral, error: Error?) {
        scan()
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral,
                        error: Error?) {
        ackCharacteristic = nil
        // A pending connect never times out on iOS; it completes when the
        // board advertises again (it re-advertises after every disconnect).
        central.connect(peripheral)
        onLinkState?(.reconnecting)
    }
}

extension BLEGateway: CBPeripheralDelegate {
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard let service = peripheral.services?.first(where: { $0.uuid == serviceUUID }) else {
            central.cancelPeripheralConnection(peripheral)
            return
        }
        peripheral.discoverCharacteristics([alertUUID, ackUUID, statusUUID], for: service)
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        for c in service.characteristics ?? [] {
            switch c.uuid {
            case alertUUID: peripheral.setNotifyValue(true, for: c)
            case ackUUID: ackCharacteristic = c
            case statusUUID:
                peripheral.setNotifyValue(true, for: c)
                peripheral.readValue(for: c)
            default: break
            }
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic,
                    error: Error?) {
        if characteristic.uuid == alertUUID, characteristic.isNotifying, ackCharacteristic != nil {
            onLinkState?(.ready)
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic,
                    error: Error?) {
        guard error == nil, let value = characteristic.value else { return }
        switch characteristic.uuid {
        case alertUUID: onAlertData?(value, peripheral.identifier.uuidString)
        case statusUUID: onStatusData?(value)
        default: break
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didWriteValueFor characteristic: CBCharacteristic,
                    error: Error?) {
        if characteristic.uuid == ackUUID {
            onAckWriteResult?(error)
        }
    }
}
