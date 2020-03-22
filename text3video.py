
import ImageTextMarker
import AudioProcessing
import cv2
import json
import hashlib
from datetime import datetime

def hash_from_file(filename):
    BLOCK_SIZE = 65536
    file_hash = hashlib.sha256()
    with open(filename, 'rb') as f:
        fb = f.read(BLOCK_SIZE)
        while len(fb) > 0:
            file_hash.update(fb)
            fb = f.read(BLOCK_SIZE)
    return file_hash.hexdigest()


video_file = "A plus 1 U5V2_Teil_1.mp4"
text_lang = "fr-FR"
audio_only = False

video_file = "Recording_Pierre.ogg"
audio_only = True


settings = {}
try:
    with open("settings.json") as jfile:
        settings = json.load(jfile)
except FileNotFoundError:
    pass


video_hash = hash_from_file(video_file)
if video_hash in settings:
    video_settings = settings[video_hash]
    text_lang = video_settings['lang']
    video_file = video_settings['filename']
else:
    video_settings = {}
    video_settings['lang'] = text_lang
    video_settings['filename'] = video_file
    settings[video_hash] = video_settings

ap = AudioProcessing.AudioProcessing()
if audio_only:
    duration = ap.set_audio_filename(video_file)
else:
    duration = ap.read_in_video(video_file)

if 'text' not in video_settings:
    print("Do speech recognition for complete text...")
    video_settings['text'] = ap.get_complete_text(text_lang)
    print("complete text: " + video_settings['text'])


itm = ImageTextMarker.ImageTextMarker()
itm.set_text(video_settings['text'])

if 'chunks' not in video_settings:
    print("Splitting audio file into chunks and do speech recognition on it...")
    video_settings['chunks'] = ap.read_markers(text_lang)

last_text_index = 0
for text, position, length in video_settings['chunks']:
    last_text_index = itm.set_marker(text, position, length, last_text_index)

if 'video_length' not in video_settings:
    video_settings['video_length'] = duration

itm.set_duration(video_settings['video_length'])


#print("Creating text.jpg with at position 12.5s...")
#cv2.imwrite("test15.jpg", itm.get_image(15))
#cv2.imwrite("test30.jpg", itm.get_image(30))
#cv2.imwrite("test60.jpg", itm.get_image(60))
#exit(0)

video_settings['frame_rate'] = 30

with open('settings.json', 'w') as outfile:
    settings['last_changed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    json.dump(settings, outfile, indent=4, ensure_ascii=False)

start_frame = 0
frame_cnt = int(video_settings['video_length']*video_settings['frame_rate'])
#start_frame = int(20*video_settings['frame_rate'])
#frame_cnt = int(30*video_settings['frame_rate'])
out_video_name = "project.avi"

print("Creating video '%s'..." % out_video_name)
#OpenCV: FFMPEG: tag 0x314d4950/'PIM1' is not supported with codec id 1 and format 'mpeg / MPEG-1 Systems / MPEG program stream'
#[mpeg1video @ 014ad3c0] MPEG-1/2 does not support 5/1 fps
#Could not open codec 'mpeg1video': Unspecified error
#out = cv2.VideoWriter('project.mpg', cv2.VideoWriter_fourcc('P','I','M','1'), video_settings['frame_rate'], (640,480))
#out = cv2.VideoWriter('project.mp4', -1, video_settings['frame_rate'], (640,480))
out = cv2.VideoWriter(out_video_name, cv2.VideoWriter_fourcc(*'XVID'), video_settings['frame_rate'], (itm.width, itm.height))

for frame in range(start_frame, frame_cnt-1):
    position = frame / video_settings['frame_rate']
    image = itm.get_image(position)
    out.write(image)

out.release()
