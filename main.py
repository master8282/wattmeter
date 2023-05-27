"""
The wattmeter code for the following hardware:
RP2040 - controller
ADS1115 - 15bit mode ADC
ACS712 - Hall current sensor with middle point for
two sides current derections
LCD1602 - standard display 
"""

from machine import I2C
from machine import Pin
from machine import Timer
import utime as time

dev = I2C(1, freq=2000000, scl=Pin(27), sda=Pin(26))
address = 72 # address ADC for i2c
val0_arr = []
val2_arr = []
wh = 0
disp_update_ms = 250

rs = machine.Pin(10,machine.Pin.OUT) # Config mc pinouts
rw = machine.Pin(9,machine.Pin.OUT)
e  = machine.Pin(8,machine.Pin.OUT)
d0 = machine.Pin(7,machine.Pin.OUT)
d1 = machine.Pin(6,machine.Pin.OUT)
d2 = machine.Pin(5,machine.Pin.OUT)
d3 = machine.Pin(4,machine.Pin.OUT)
d4 = machine.Pin(3,machine.Pin.OUT)
d5 = machine.Pin(2,machine.Pin.OUT)
d6 = machine.Pin(1,machine.Pin.OUT)
d7 = machine.Pin(0,machine.Pin.OUT)
 
def send2LCD8(BinNum):
    """Sending 8bit command to LCD register"""
    d0.value((BinNum & 0x1) >>0)
    d1.value((BinNum & 0x2) >>1)
    d2.value((BinNum & 0x4) >>2)
    d3.value((BinNum & 0x8) >>3)
    d4.value((BinNum & 0x10) >>4)
    d5.value((BinNum & 0x20) >>5)
    d6.value((BinNum & 0x40) >>6)
    d7.value((BinNum & 0x80) >>7)
    e.value(1)
    e.value(0)

def disp(x,y,data):
    """Setting up lcd cursor in xy position and display text"""
    rs.value(0)
    if not y:
        send2LCD8(0x80) # Line 0 of LCD y-axel 
    else:
        send2LCD8(0xc0) # Line 1 of LCD y-axel
    for i in range(x):
        send2LCD8(0x14) # Steps from the begining x-axel
    rs.value(1)
    
    for char in data:
       send2LCD8(ord(char)) # iterate over chars of string in unicode
    
def setUpLCD():
    """ Init LCD mode and params """
    rs.value(0)
    send2LCD8(0x38) # 8bit,2 lines?,5*8 bots
    send2LCD8(0xc)  # LCD on, blink off, cursor off.
    send2LCD8(0x1)  # clear screen
    time.sleep_ms(2)# clear screen needs a some delay
    rs.value(1)
    disp(0,0,"V:      A:") # Constant menu lbels
    disp(0,1,"P:      W:")

def writeadc():
    """Writing ADC register"""
    dev.writeto(address, bytearray([1]))
    result = dev.readfrom(address, 2)
    return result[0] << 8 | result[1]
 
def readadc(channel):
    """Reading ADC register"""
    adc = writeadc()  
    adc &= ~(7 << 12) # clear MUX bits
    adc &= ~(7 << 9)  # clear PGA
    adc |= (7 & (4 + channel)) << 12 # choise channel
    adc |= (1 << 15)  # trigger next conversion
    adc |= (1 << 9)   # gain 5v
    adc = [int(adc >> i & 0xff) for i in (8, 0)]
    dev.writeto(address, bytearray([1] + adc))
    adc = writeadc()
    
    while (adc & 0x8000) == 0:
        adc = writeadc() 
    dev.writeto(address, bytearray([0]))
    result = dev.readfrom(address, 2)
    return result[0] << 8 | result[1]

def disp_update(timer):
    """Write dinamic values down LCD"""
    global val0_arr, val2_arr, wh
    val0_arr = sum(val0_arr)/len(val0_arr)
    val2_arr = sum(val2_arr)/len(val2_arr)
    w = val0_arr*val2_arr
    wh += w/(3600 * (1000/disp_update_ms))
    disp(2,0,f"{val0_arr:.2f} ") # menu value positions
    disp(10,0,f"{val2_arr:.3f} ")
    disp(2,1,f"{w:.1f} ")
    disp(10,1,f"{wh:.3f}  ")
    val0_arr = []
    val2_arr = []

if __name__ == "__main__":
    soft_timer = Timer(mode=Timer.PERIODIC,
        period=disp_update_ms,
        callback=disp_update
        )
    setUpLCD()

    while True:
        val0 = readadc(0)
        val2 = abs(readadc(2) - 19800)
        if val0 > 32767: # Max steps for ADS1115 is 32767
                         # But when 0 volts it shows 65564
                         # And makes mess
            val0 = 0
        if 30 > val2:    # To avoid ADC noise when 0 volts
            val2 = 0
        val0_arr.append(val0/32767*59.92) # 32767 max val for chan0
                                          # 59.92 is almost 60v but 
                                          # provvides more accurancy
        val2_arr.append(val2/7280*5.00)   # 7280 max val for 5 amp for 
                                          # acs712
