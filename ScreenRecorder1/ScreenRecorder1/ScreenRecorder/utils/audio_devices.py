import sounddevice as sd

def get_input_devices():
    result = []
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            result.append({"index": index, "name": device["name"], "channels": device["max_input_channels"]})
    return result

def print_audio_devices():
    for item in get_input_devices():
        print(f'{item["index"]}: {item["name"]} | Input Channels: {item["channels"]}')
