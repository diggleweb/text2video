# pip install --user pillow
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import numpy as np
import cv2
import queue


class ImageTextMarker():
    def __init__(self):
        self.width = 1440 #640
        self.height = 1080 #480
        self.__margin_top  = 100
        self.__margin_side = 25
        self.__line_margin = 5
        self.__lines = []
        self.__raw_words = []
        self.__markers = { }            # __raw_words index : position in seconds
        self.__word_height = 0
        self.__duration = 0
        # create transparent image
        self.__font = ImageFont.truetype('Arial.ttf', 45)
        # will be overwritten in __update_image()
        self.__text_img = Image.new('RGBA', (self.width, self.height), color=(255, 0, 0, 0))
        self.__draw = ImageDraw.Draw(self.__text_img)
        self.__sep_len = self.__draw.textsize(text=' ', font=self.__font)[0]
        self.__pos_fifo = {}


    def __update_image(self):
        text_img_height = self.__margin_top + (len(self.__lines)+1)*self.__word_height
        if text_img_height < self.height:
            text_img_height = self.height
        print("Image height: %d" % text_img_height)
        self.__text_img = Image.new('RGBA', (self.width, text_img_height), color=(255, 0, 0, 0))
        self.__draw = ImageDraw.Draw(self.__text_img)
        self.__sep_len = self.__draw.textsize(text=' ', font=self.__font)[0]
        self.__pos_fifo = {}
        offset_y = self.__margin_top
        for line in self.__lines:
            offset_x = self.__margin_side
            for word in line:
                size = self.__draw.textsize(text=word, font=self.__font)
                width = size[0]
                if offset_x + self.__sep_len + width + self.__margin_side > self.width:
                    offset_y = offset_y + self.__word_height
                    if offset_y > self.__text_img.height:
                        print("ERROR in image height calculation!!!! %d > %d" % (offset_y, self.__text_img.height))
                        break
                    offset_x = self.__margin_side
                self.__draw.text((offset_x, offset_y), word, font=self.__font, fill=(0, 0, 0))
                offset_x = offset_x + self.__sep_len + width
            offset_y = offset_y + self.__word_height
            if offset_y > self.__text_img.height:
                print("ERROR in image height calculation! %d > %d" % (offset_y, self.__text_img.height))
                break

    def set_text(self, text):
        self.__lines = []
        for line in text.split('\n'):
            words = line.split(' ')
            self.__lines.append(words)
            for word in words:
                if len(word) > 0:
                    self.__raw_words.append(word.lower().strip('-;:.,!?\t"'))
        self.__word_height = self.__max_word_height() + self.__line_margin
        self.__update_image()

    def __len__(self):
        return len(self.__raw_words)

    def set_total_time(self, time):
        self.__word_times[-1] = time

    def __find_best_match(self, haystack, needle, index_hint):
        result = []
        result_indexes = []
        for n_index, n_word in enumerate(needle):
            for h_index, h_word in enumerate(haystack):
                start_index = h_index - n_index
                if n_word != h_word:
                    continue
                if start_index in result_indexes:
                    continue
                match_count = 0
                for index, word in enumerate(needle.copy()):
                    if (start_index+index) < len(haystack) and word == haystack[start_index+index]:
                        match_count = match_count + 1
                hint_distance = abs(index_hint - start_index)
                quality = match_count / len(needle)
                result.append( (start_index, match_count / len(needle), hint_distance) )
                result_indexes.append(start_index)
        return result

    def set_marker(self, text, position, length, index_hint):
        words = text.lower().strip('-;:.,!?\t"').split(' ')
        matches = self.__find_best_match(self.__raw_words, words, index_hint)
        if len(matches) == 0:
            print("NOT FOUND: " + str(text))
        else:
            prio_matches = queue.PriorityQueue()
            for index, quality, hint_distance in matches:
                #print("%s - %f+%f/50 %d" % (text, -quality, hint_distance, index))
                prio_matches.put( (-quality+hint_distance/50, index) )
            quality_dist, index = prio_matches.get()
            if -quality_dist >= 0.8:
                #print("xx %d %f - %s" % (index_hint, quality_dist, str(matches)))
                print("Marker: %d - %f" % (index, position))
                self.__markers[index] = position
                print("Marker: %d - %f" % (index+len(words), position+length))
                self.__markers[index+len(words)-1] = position+length
                return index + len(words) - 1
            elif -quality_dist >= 0.5:
                if len(prio_matches.queue) > 1:
                    next_quality, next_index = prio_matches.get()
                    if (-quality_dist+next_quality) <= 0.2:
                        print("SKIPPED '" + text + "' - quality "+str(quality_dist)+"|"+str(next_quality)+" too similar: " + str(matches))
                        if index_hint == 0:
                            return index_hint
                        return index_hint + len(words)
                print("Marker: %d - %f" % (index, position))
                self.__markers[index] = position
                print("Marker: %d - %f" % (index+len(words), position+length))
                self.__markers[index+len(words)-1] = position+length
                return index + len(words) - 1
            else:
                print("SKIPPED '" + text + "' - quality " + str(quality_dist) + " too bad: " + str(matches))
        if index_hint == 0:
            return index_hint
        return index_hint + len(words)


    def __max_word_height(self):
        max_height = 0
        for line in self.__lines:
            for word in line:
                height = self.__draw.textsize(text=word, font=self.__font)[1]
                if height > max_height:
                    max_height = height
        return max_height


    def set_duration(self, duration):
        self.__duration = duration


    def __get_highlighted(self, position):
        start_position = 0
        start_index = 0
        for marker_index, marker_position in self.__markers.items():
            if marker_position <= position:
                start_position = marker_position
                start_index = marker_index
            else:
                diff_position = marker_position - start_position
                diff_index = marker_index - start_index
                return start_index + int(diff_index/diff_position*(position-start_position))
        diff_position = self.__duration - start_position
        diff_index = len(self.__raw_words) - start_index
        return start_index + int(diff_index/diff_position*(position-start_position))


    def get_image(self, position):
        highlighted = self.__get_highlighted(position)
        highlighted_line_y = -1
        background = Image.new('RGB', (self.width, self.__text_img.height), color=(255, 255, 255))
        background_draw = ImageDraw.Draw(background)
        word_cnt = 0
        offset_y = self.__margin_top
        for line in self.__lines:
            offset_x = self.__margin_side
            for word in line:
                size = self.__draw.textsize(text=word, font=self.__font)
                width = size[0]
                if offset_x + self.__sep_len + width + self.__margin_side > self.width:
                    offset_y = offset_y + self.__word_height
                    if offset_y > self.__text_img.height:
                        print("ERROR in bg image height calculation: %d > %d" % (offset_y, self.__text_img.height))
                        break
                    offset_x = self.__margin_side
                if word_cnt == highlighted:
                    if len(word) > 0:
                        background_draw.rectangle([offset_x-2, offset_y, offset_x+size[0]+2, offset_y+self.__word_height], fill=(255,0,0))
                    highlighted_line_y = offset_y
                    #break
                #if word_cnt in self.__markers:
                #    background_draw.line([(offset_x-3, offset_y), (offset_x-3, offset_y+self.__word_height)], fill=(255, 255, 0))
                #    background_draw.text((offset_x, offset_y-5), "%3.3f (%d)" % (self.__markers[word_cnt], word_cnt),
                #                         font=ImageFont.truetype('Arial.ttf', 22), fill=(255, 255, 0))
                if len(word) > 0:
                    word_cnt = word_cnt + 1
                offset_x = offset_x + self.__sep_len + width
            offset_y = offset_y + self.__word_height
            if offset_y > self.__text_img.height:
                print("ERROR in background image height calculation: %d > %d" % (offset_y, self.__text_img.height))
                break

        # merge text image with background image
        background.paste(self.__text_img, (0, 0), self.__text_img)

        # moving average of 6 seconds
        self.__pos_fifo[position] = highlighted_line_y - self.height / 2
        delete = [pos_t for pos_t in self.__pos_fifo if (position-pos_t) > 6.0]
        for pos_t in delete: del self.__pos_fifo[pos_t]
        y_move = 0
        for pos_t, pos_y in self.__pos_fifo.items():
            y_move = y_move + pos_y
        y_move = y_move / len(self.__pos_fifo)

        if (self.__text_img.height-y_move) < self.height:
            y_move = self.__text_img.height - self.height
        elif y_move < 0:
            y_move = 0
        print("%3.3f - move=%5d high=%5d - %3d %s" % (position, y_move, highlighted_line_y, highlighted, self.__raw_words[highlighted]))

        background = background.crop((0, y_move, self.width, self.height+y_move))
        #background_draw.text((self.width - 150, self.__margin_side), "POS=%3.3f" % position,
        #                     font=ImageFont.truetype('Arial.ttf', 22), fill=(255, 0, 0))
        #background.show("image")
        #background.save("pillow.png", quality=100)
        return cv2.cvtColor(np.array(background), cv2.COLOR_RGB2BGR)