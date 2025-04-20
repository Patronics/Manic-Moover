import machine
import socket
import network
import time

# PWM setup
# these pins share a slice, so same freq but different duty cycle
pwm_pin_left = machine.Pin(14)
pwm_pin_right = machine.Pin(15)

forward_pin_left = machine.Pin(10)
reverse_pin_left = machine.Pin(11)
# these two aren't yet used because we don't have enough relays
forward_pin_right = machine.Pin(12)
reverse_pin_left = machine.Pin(13)

current_direction = "forward"



pwm_left = machine.PWM(pwm_pin_left)
pwm_left.freq(200)
pwm_left.duty_u16(0)
pwm_right = machine.PWM(pwm_pin_right)
pwm_right.freq(200)
pwm_right.duty_u16(0)

speed_left = None
speed_right = None
my_ip = None

#stop to allow h-bridge relays to settle along with motion
def momentary_stop():
    pwm_left.duty_u16(65535)
    pwm_right.duty_u16(65535)
    forward_pin_left.value(0)
    reverse_pin_left.value(0)
    forward_pin_right.value(0)
    reverse_pin_right.value(0)
    time.sleep(0.25) #time for motion to stop
    return



def handle_request(request):
    print("Request:", request)
    global speed_left
    global speed_right
    
    if '/speed/' in request:
        try:
            parts = request.split('/speed/')
            speed_left = int(parts[1].split()[0])
            if(current_direction == "forward" or current_direction == "spin_left"):  #todo reverse and tight turns, same logic
                speed_right = speed_left
            else:
                speed_right = 0
        except:
            speed_left = None
            speed_right = None
        
    elif '/forward/' in request:
        momentary_stop()
        forward_pin_left.value(1)
        forward_pin_right.value(1)
        
    elif '/stop/' in request:
        momentary_stop()
        #no direction pins set, stops with speed preserved

    elif '/emergencystop/' in request:
        momentary_stop()
        speed_left = 0
        speed_right = 0
        #reset speeds to 0 too
    #show web interface
    else:
        html = """<!DOCTYPE html>
            <html>
                <style>
                  body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    background-color: #f0f0f0;
                  }}

                  h1 {{
                    color: #333;
                  }}

                  table {{
                    margin: 20px auto;
                  }}

                  button {{
                    padding: 15px 25px;
                    font-size: 16px;
                    margin: 10px;
                    border: none;
                    border-radius: 8px;
                    background-color: #4CAF50;
                    color: white;
                    cursor: pointer;
                    transition: background-color 0.3s ease;
                    min-width: 100px;
                  }}

                  button:hover {{
                    background-color: #45a049;
                  }}

                  #speedSlider {{
                    width: 300px;
                    margin: 20px;
                  }}

                  #speedDisplay {{
                    font-size: 18px;
                    font-weight: bold;
                  }}
                </style>

              <body>
                <input type="range" min="0" max="255" value="0" id="speedSlider">
                <span id="speedDisplay">0</span>
                <table>
                    <tr>
                        <td><button id="turnLeft" onclick="sendMove('turnLeft')">Turn Left</button></td>
                        <td><button id="forward" onclick="sendMove('forward')">Forward</button></td>
                        <td><button id="turnRight" onclick="sendMove('turnRight')">Turn Right</button></td>
                    </tr>
                    <tr>
                        <td><button id="spinLeft" onclick="sendMove('spinLeft')">Spin Left</button></td>
                        <td><button id="stop" onclick="sendMove('stop')">Stop</button></td>
                        <td><button id="spinRight" onclick="sendMove('spinRight')">Spin Right</button></td>
                    </tr>
                    <tr>
                        <td><button id="spinBackLeft" onclick="sendMove('spinBackLeft')">Spin Back-Left</button></td>
                        <td><button id="reverse" onclick="sendMove('reverse')">Reverse</button></td>
                        <td><button id="spinBackRight" onclick="sendMove('spinBackRight')">Spin Back-Right</button></td>
                    </tr>

                </table>

                <script>
                
                function sendMove(moveType){{
                    fetch(`http://{ip}/${{moveType}}`)
                    .then(res => res.text())
                    .then(console.log)
                    .catch(console.error);
                }}
                window.sendMove = sendMove   
                
                const slider = document.getElementById('speedSlider');
                const display = document.getElementById('speedDisplay');
                let lastSent = 0;
                  
                  

                slider.addEventListener('input', () => {{
                    const val = slider.value;
                    display.textContent = val;

                    // Throttle or debounce as needed
                    if (Math.abs(val - lastSent) > 2) {{
                        fetch(`http://{ip}/speed/${{val}}`)
                        .then(res => res.text())
                        .then(console.log)
                        .catch(console.error);
                    lastSent = val;
                    }}
                }});
                </script>
              </body>
            </html>
            """.format(ip = my_ip)
        return html

    if speed_left is not None:
        # Clamp and scale to 16-bit PWM value
        print("Setting speed left:", speed_left, "right:", speed_right)
        speed_left = max(0, min(255, speed_left))
        speed_right = max(0, min(255, speed_right))
        pwm_left.duty_u16(65535-int(speed_left * 257))  # Scale 0–255 to 0–65535
        pwm_right.duty_u16(65535-int(speed_right * 257))  # Scale 0–255 to 0–65535
        return f"Speed set to left: {speed_left}, right: {speed_right}"
    else:
        return "Invalid or missing speed"


ssid = 'if (wifi != connected){'
password = 'connected==true;}'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)



max_wait = 10
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')
    time.sleep(1)

if wlan.status() != 3:
    raise RuntimeError('network connection failed')
else:
    print('connected')
    status = wlan.ifconfig()
    print( 'ip = ' + status[0] )
    my_ip = status[0]

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(addr)
sock.listen(1)

print('listening on', addr)

# Listen for connections
while True:
    try:
        cl, addr = sock.accept()
        print('client connected from', addr)
        
        request = cl.recv(1024).decode()

        response = handle_request(request)

        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(response)
        cl.close()

    except OSError as e:
        cl.close()
        print('connection closed')