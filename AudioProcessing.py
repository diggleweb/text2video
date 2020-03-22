import moviepy.editor as mp
import os

from pydub import AudioSegment
from pydub.silence import split_on_silence
import speech_recognition as sr



class AudioProcessing():
    def __init__(self):
        ffmpeg_path = "C:\\Users\\Charly\\PycharmProjects\\Text3Video\\ffmpeg-4.2.2-win32-static\\bin\\"
        os.environ['PATH'] = ';'.join([os.getenv('PATH'), ffmpeg_path])
        self.__audio_filename = "extracted_audio.wav"
        self.__r = sr.Recognizer()
        print("Included speech recognition in version %s" % sr.__version__)

        pass

    def read_in_video(self, filename):
        print("Read in %s" % filename)
        clip = mp.VideoFileClip(filename)  # .subclip(0,3)
        # fps = clip.fps
        # array = clip.audio.to_soundarray(nbytes=1, fps=fps)
        # print("fps=" + str(fps) + " len=" + str(len(array)))
        # print(array)
        print("Writing audio of %s to %s" % (filename, self.__audio_filename))
        clip.audio.write_audiofile(self.__audio_filename)
        return clip.duration

    def __find_index(self, haystack, needle, first_index=0):
        clipped_haystack = haystack[first_index:]
        length = len(needle)
        for index, value in enumerate(clipped_haystack):
            if needle[0] != value:
                continue
            if needle == clipped_haystack[index: index + length]:
                return index + first_index
        return -1

    def set_audio_filename(self, audiofile):
        print("Converting %s to %s..." % (audiofile, self.__audio_filename))
        sound = AudioSegment.from_file(audiofile)
        sound.export(self.__audio_filename, format='wav')
        return sound.duration_seconds

    def get_complete_text(self, text_lang):
        print("Convert %s to text..." % self.__audio_filename)
        with sr.AudioFile(self.__audio_filename) as source:
            audio = self.__r.record(source)
            return self.__r.recognize_google(audio, language=text_lang)

    def read_markers(self, text_lang):
        markers = []
        silence_sec = 0.4
        sound = AudioSegment.from_file(self.__audio_filename)
        print("Splitting sound by silence..")
        silent_chunks = split_on_silence(sound,
                                  # must be silent for at least half a second
                                  min_silence_len=int(1000 * silence_sec),
                                  silence_thresh=sound.dBFS - 6,
                                  keep_silence=int(1000 * silence_sec)
                            )
        last_index = 0
        for i, chunk in enumerate(silent_chunks):
            index = self.__find_index(
                sound.raw_data,
                chunk.raw_data,
                last_index)
            last_index = index
            samples_per_second = len(sound.raw_data) / sound.duration_seconds
            position = index / samples_per_second
            print("%3d | %5.3f | %8d | %.3f" %
                  (i, chunk.duration_seconds, index, position))

            filename = "chunk{0}.wav".format(i)
            chunk.export(filename, format="wav")

            try:
                with sr.AudioFile(filename) as source:
                    audio = self.__r.record(source)
                    text = self.__r.recognize_google(audio, language=text_lang)

                    markers.append( (text, position + silence_sec, chunk.duration_seconds - 2 * silence_sec) )

                    print("chunk %s at %f: '%s'" % (filename, position, text))
            except sr.UnknownValueError:
                print("chunk %s at %f: %s" % (filename, position, "--NOT_RECOGNIZED--"))

        return markers



