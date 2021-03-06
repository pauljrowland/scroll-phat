MODE_5X11 = 0b00000011

class IS31FL3730:
    def __init__(self, smbus, font):
        self.smbus = smbus
        self.font = font

        self.I2C_ADDR = 0x60
        self.CMD_SET_MODE = 0x00
        self.CMD_SET_BRIGHTNESS = 0x19
        self.MODE_5X11 = 0b00000011

    def initialize(self):
        self.bus = self.smbus.SMBus(1)
        self.buffer = [0] * 11
        self.offset = 0
        self.error_count = 0
        self.rotate = False
        self.set_mode(self.MODE_5X11)

    def rotate5bits(self, x):
        r = 0
        if x & 16:
            r = r | 1
        if x & 8:
            r = r | 2
        if x & 4:
            r = r | 4
        if x & 2:
            r = r | 8
        if x & 1:
            r = r | 16
        return r

    def update(self):
        if self.offset + 11 <= len(self.buffer):
            self.window = self.buffer[self.offset:self.offset + 11]
        else:
            self.window = self.buffer[self.offset:]
            self.window += self.buffer[:11 - len(self.window)]

        if self.rotate:
            self.window.reverse()
            for i in range(len(self.window)):
                self.window[i] = self.rotate5bits(self.window[i])

        self.window.append(0xff)

        try:
            self.bus.write_i2c_block_data(self.I2C_ADDR, 0x01, self.window)
        except IOError:
            self.error_count += 1
            if self.error_count == 10:
                print("A high number of IO Errors have occurred, please check your soldering/connections.")

    def set_mode(self, mode=MODE_5X11):
        self.bus.write_i2c_block_data(self.I2C_ADDR, self.CMD_SET_MODE, [self.MODE_5X11])

    def set_brightness(self, brightness):
        self.brightness = brightness
        self.bus.write_i2c_block_data(self.I2C_ADDR, self.CMD_SET_BRIGHTNESS, [self.brightness])

    def set_col(self, x, value):
        if len(self.buffer) <= x:
            self.buffer += [0] * (x - len(self.buffer) + 1)

        self.buffer[x] = value

    def write_string(self, chars, x = 0):
        for char in chars:
            if ord(char) == 0x20 or ord(char) not in self.font:
                self.set_col(x, 0)
                x += 1
                self.set_col(x, 0)
                x += 1
                self.set_col(x, 0)
                x += 1
            else:
                font_char = self.font[ord(char)]
                for i in range(0, len(font_char)):
                    self.set_col(x, font_char[i])
                    x += 1

                self.set_col(x, 0)
                x += 1 # space between chars
        self.update()

    # draw a graph across the screen either using
    # the supplied min/max for scaling or auto
    # scaling the output to the min/max values
    # supplied
    def graph(self, values, low=None, high=None):
        if low == None:
            low = min(values)

        if high == None:
            high = max(values)

        span = high - low

        col = 0
        for value in values:
            value -= low
            value /= span
            value *= 5
            value = int(value)

            bits = 0
            if value > 1:
                bits |= 0b10000
            if value > 2:
                bits |= 0b11000
            if value > 3:
                bits |= 0b11100
            if value > 4:
                bits |= 0b11111
            if value > 5:
                bits |= 0b11111
            self.set_col(col, bits)
            col += 1

        self.update()

    def set_buffer(self, replacement):
        self.buffer = replacement

    def buffer_len(self):
        return len(self.buffer)

    def scroll(self, delta = 1):
        self.offset += delta
        self.offset %= len(self.buffer)
        self.update()

    def clear(self):
        self.offset = 0
        self.buffer = [0] * 11
        self.update()

    def load_font(self, new_font):
        self.font = new_font

    def scroll_to(self, pos = 0):

        self.offset = pos
        self.offset %= len(self.buffer)
        self.update()

    def io_errors(self):
        return self.error_count

    def set_pixel(self, x,y,value):
        if value:
            self.buffer[x] |= (1 << y)
        else:
            self.buffer[x] &= ~(1 << y)
