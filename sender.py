import socket
import time
import smbus

# Bluetooth code
serverMACAddress = 'D8:3A:DD:3C:DF:DE'
port = 4
s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
s.connect((serverMACAddress, port))

# ADC code
ADC_ADDRESS = 0x4b
ADC_CHANNEL = 0

def read_adc():
    bus = smbus.SMBus(1)
    adc_value = bus.read_word_data(ADC_ADDRESS, 0x40 | (ADC_CHANNEL & 0x03))
    return adc_value

if __name__ == '__main__':
    GAIN = 2/3  
    curState = 0
    thresh = 525  
    P = 512 #peak signal
    T = 512 #sensitivity of the signal
    stateChanged = 0
    sampleCounter = 0
    lastBeatTime = 0
    firstBeat = True
    secondBeat = False
    Pulse = False
    IBI = 600
    rate = [0] * 10
    amp = 100
    lastTime = int(time.time() * 1000)

    while True:
        Signal = read_adc()
        curTime = int(time.time() * 1000)
        sampleCounter += curTime - lastTime
        lastTime = curTime
        N = sampleCounter - lastBeatTime #pulse intervel

        if Signal < thresh and N > (IBI/5.0)*3.0:
            if Signal < T:
                T = Signal

        if Signal > thresh and Signal > P:
            P = Signal

        if N > 250:
            if (Signal > thresh) and (Pulse == False) and (N > (IBI/5.0)*3.0):
                Pulse = True
                IBI = sampleCounter - lastBeatTime
                lastBeatTime = sampleCounter

                if secondBeat:
                    secondBeat = False

                if firstBeat:
                    firstBeat = False
                    secondBeat = True
                    continue

                runningTotal = 0

                for i in range(0, 9):
                    rate[i] = rate[i + 1]
                    runningTotal += rate[i]

                rate[9] = IBI
                runningTotal += rate[9]
                runningTotal /= 10
                BPM = 60000 / runningTotal
                if BPM >= 50 and BPM <= 200:
                    print('BPM: {}'.format(BPM))
                    # Send BPM through Bluetooth
                    bpm_str = str(BPM)
                    s.send(bytes(bpm_str, 'UTF-8'))
                else:
                    pass

        if Signal < thresh and Pulse:
            Pulse = False
            amp = P - T
            thresh = amp/2 + T
            P = thresh
            T = thresh

        if N > 2500:
            thresh = 512
            P = 512
            T = 512
            lastBeatTime = sampleCounter
            firstBeat = True
            secondBeat = False
            print("no beats found")

        time.sleep(0.025)