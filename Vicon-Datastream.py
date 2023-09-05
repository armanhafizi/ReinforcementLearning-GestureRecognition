from __future__ import print_function
from vicon_dssdk import ViconDataStream
import argparse
import numpy as np
from pynput import keyboard

def on_press(key):
    global record, rows
    try:
        if key.char == 's':
            print('Record started')
            rows = []
            record = True
        elif key.char == 'f':
            data.append(rows)
            print('Record finished', len(data))
            record = False
    except:
        print('invalid key')
    

def on_release(key):
    global done
    if key == keyboard.Key.esc:
        print('DONE')
        done = True
        return False # Stop listener

# ...or, in a non-blocking fashion:
listener = keyboard.Listener(on_press=on_press,on_release=on_release)
listener.start()

data, rows = [], []
done, record = False, False

def getCenter(X, Y, Z):
    x = sum(X)/len(X)
    y = sum(Y)/len(Y)
    z = sum(Z)/len(Z)
    return x, y, z

parser = argparse.ArgumentParser(description=__doc__)
# parser.add_argument('host', nargs='?', help="Host name, in the format of server:port", default = "localhost:801")
parser.add_argument('host', nargs='?', help="Host name, in the format of server:port", default = "169.254.12.202")
args = parser.parse_args()

client = ViconDataStream.Client()

try:
    client.Connect( args.host )
    client.SetBufferSize( 1 )

    #Enable all the data types
    client.EnableSegmentData()
    client.EnableMarkerData()
    client.EnableUnlabeledMarkerData()
    client.EnableMarkerRayData()
    client.EnableDeviceData()
    client.EnableCentroidData()
    while True:
        HasFrame = False
        while not HasFrame:
            try:
                client.GetFrame()
                HasFrame = True
            except ViconDataStream.DataStreamException as e:
                client.GetFrame()
        
        # Try setting the different stream modes
        client.SetStreamMode( ViconDataStream.Client.StreamMode.EClientPull )
        client.SetStreamMode( ViconDataStream.Client.StreamMode.EClientPullPreFetch )
        client.SetStreamMode( ViconDataStream.Client.StreamMode.EServerPush )
        client.GetFrame(), client.GetFrameNumber()
        client.SetAxisMapping( ViconDataStream.Client.AxisMapping.EForward, ViconDataStream.Client.AxisMapping.ELeft, ViconDataStream.Client.AxisMapping.EUp )
        xAxis, yAxis, zAxis = client.GetAxisMapping()
        try:
            client.ConfigureWireless()
        except ViconDataStream.DataStreamException as e:
            print( 'Failed to configure wireless', e )

        # objects: index, middle
        subjectNames = client.GetSubjectNames()
        row = [0 for i in range(3)]
        valid = True
        for subjectName in subjectNames:
            markerNames = client.GetMarkerNames( subjectName )
            X, Y, Z = [], [], []
            for markerName, parentSegment in markerNames:
                position = list(list(client.GetMarkerGlobalTranslation( subjectName, markerName ))[0])
                X.append(position[0])
                Y.append(position[1])
                Z.append(position[2])
            x, y, z = getCenter(X, Y, Z)
            if x == 0.0 and y == 0.0 and z == 0.0:
                valid = False
                break
            if subjectName == 'RL-thumb':
                row[0] = [x, y, z]
            elif subjectName == 'RL-index':
                row[1] = [x, y, z]
            elif subjectName == 'RL-middle':
                row[2] = [x, y, z]
        if valid and record:
            rows.append(row)
            print('.', end='')
        if done:
            break

    modes = ['circle-cw', 'circle-ccw', 'swipe-r', 'swipe-l', 'swipe-u', 'swipe-d', 'swipe-f', 'swipe-b', 'ok', 'stop']
    mode = modes[8]
    # save dataset
    data = np.array(data, dtype=object)
    filename = 'data/' + mode + '.npy'
    np.save(filename, data, allow_pickle=True)
    read = np.load(filename, allow_pickle=True)
    print(read == data)
    print(read.shape)
    # print(data)

except ViconDataStream.DataStreamException as e:
    print( 'Handled data stream error', e )
